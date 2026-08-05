import datetime
import json

import anvil
import anvil.email
import anvil.server
import anvil.tables as tables
from anvil.tables import app_tables

import logic


def _subscriber(token):
    token = (token or "").strip()
    return app_tables.subscribers.get(token=token) if token else None


def _link_dict(row):
    return {"id": row.get_id(), "url": row["url"], "title": row["title"],
            "saved": row["saved"], "fetched_at": row["fetched_at"],
            "tags": row["tags"] or "", "note": row["note"] or "",
            "stars": logic.link_stars(row["stars"], row["starred"])}


def _jsonable(d):
    out = dict(d)
    for k in ("saved", "fetched_at"):
        out[k] = out[k].isoformat(sep=" ", timespec="minutes") if out[k] else None
    return out


def _html(body, status):
    resp = anvil.server.HttpResponse(status, body)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return resp


def _json(payload, status):
    resp = anvil.server.HttpResponse(status, json.dumps(payload))
    resp.headers["Content-Type"] = "application/json"
    return resp


@anvil.server.callable
def register_email(email):
    email_n = logic.normalize_email(email)
    if not logic.valid_email(email_n):
        return {"ok": False, "error": "Please enter a valid email address."}
    today = datetime.date.today()
    row = app_tables.subscribers.get(email=email_n)
    prev_date = row["reg_date"] if row else None
    prev_count = (row["reg_count"] if row else 0) or 0
    count = logic.next_reg_count(prev_date, prev_count, today)
    if count is None:
        return {"ok": False,
                "error": "Too many registrations today. Try again tomorrow."}
    token = logic.new_token()
    if row:
        row.update(token=token, reg_date=today, reg_count=count)
    else:
        app_tables.subscribers.add_row(
            email=email_n, token=token,
            created=datetime.datetime.now(),
            reg_date=today, reg_count=count)
    anvil.email.send(
        from_name="send2me", to=email_n,
        subject="Your send2me key",
        text=logic.registration_email_text(
            token, logic.bookmarklet_js(token), logic.links_page_url(token)))
    return {"ok": True}


@anvil.server.callable
def make_bookmarklet(token):
    token = (token or "").strip()
    row = app_tables.subscribers.get(token=token) if token else None
    if row is None:
        return {"ok": False,
                "error": "Unknown key. Check that you pasted the entire key from the email."}
    return {"ok": True, "js": logic.bookmarklet_js(token),
            "links_url": logic.links_page_url(token)}


def _enforce_cap(email):
    """Holder brukeren under logic.MAX_LINKS, som e-posten lover. len() pa et
    Anvil-sok er en billig telling, sa vanlige lagringer koster ingen henting."""
    rows = app_tables.links.search(email=email)
    if len(rows) <= logic.MAX_LINKS:
        return 0
    doomed = set(logic.links_over_cap(
        [{"id": r.get_id(), "saved": r["saved"],
          "stars": logic.link_stars(r["stars"], r["starred"])} for r in rows]))
    n = 0
    for r in app_tables.links.search(email=email):
        if r.get_id() in doomed:
            r.delete()
            n += 1
    return n


@anvil.server.http_endpoint("/sendlink")
def sendlink(**kwargs):
    params = anvil.server.request.query_params
    url = params.get("url") or ""
    title = params.get("title") or ""
    row = _subscriber(params.get("token"))
    if row is None:
        return _html(logic.error_page_html(
            "Unknown key. Register at send2me.app."), 403)
    if not url:
        return _html(logic.error_page_html("Missing URL."), 400)
    mode = logic.normalize_mode(row["mode"])
    if mode != "email":
        app_tables.links.add_row(
            email=row["email"], url=url, title=title,
            saved=datetime.datetime.now(), fetched_at=None,
            tags=logic.normalize_tags(row["current_tag"]),
            note="", stars=0, starred=False)
        _enforce_cap(row["email"])
    if mode != "save":
        anvil.email.send(
            from_name="send2me", to=row["email"],
            subject=(title or url), text=url)
    return _html(logic.sent_page_html("Saved" if mode == "save" else "Sent"), 200)


@anvil.server.callable
def get_settings(token):
    row = _subscriber(token)
    if row is None:
        return {"ok": False, "error": "Unknown key."}
    return {"ok": True, "email": row["email"],
            "mode": logic.normalize_mode(row["mode"]),
            "current_tag": row["current_tag"] or ""}


@anvil.server.callable
def save_settings(token, mode=None, current_tag=None):
    """Bare feltene som sendes inn endres - modus bor i innstillings-modalen,
    current tag i overskriften, og de lagrer seg hver for seg."""
    row = _subscriber(token)
    if row is None:
        return {"ok": False, "error": "Unknown key."}
    if mode is not None:
        row["mode"] = logic.normalize_mode(mode)
    if current_tag is not None:
        row["current_tag"] = logic.normalize_tags(current_tag)
    return {"ok": True, "mode": logic.normalize_mode(row["mode"]),
            "current_tag": row["current_tag"] or ""}


@anvil.server.callable
def get_my_links(token):
    row = _subscriber(token)
    if row is None:
        return {"ok": False, "error": "Unknown key."}
    rows = app_tables.links.search(tables.order_by("saved", ascending=False),
                                   email=row["email"])
    return {"ok": True, "links": [_jsonable(_link_dict(r)) for r in rows]}


def _own_link(token, link_id):
    row = _subscriber(token)
    if row is None:
        return None
    link = app_tables.links.get_by_id(link_id)
    if link is None or link["email"] != row["email"]:
        return None
    return link


@anvil.server.callable
def update_link(token, link_id, tags=None, note=None, stars=None):
    link = _own_link(token, link_id)
    if link is None:
        return {"ok": False, "error": "Not found."}
    if tags is not None:
        link["tags"] = logic.normalize_tags(tags)
    if note is not None:
        link["note"] = (note or "").strip()
    if stars is not None:
        n = logic.clamp_stars(stars)
        link.update(stars=n, starred=n > 0)
    return {"ok": True, "tags": link["tags"] or "",
            "stars": logic.link_stars(link["stars"], link["starred"])}


@anvil.server.callable
def delete_link(token, link_id):
    link = _own_link(token, link_id)
    if link is None:
        return {"ok": False, "error": "Not found."}
    link.delete()
    return {"ok": True}


@anvil.server.callable
def delete_all_links(token):
    row = _subscriber(token)
    if row is None:
        return {"ok": False, "error": "Unknown key."}
    n = 0
    for link in app_tables.links.search(email=row["email"]):
        link.delete()
        n += 1
    return {"ok": True, "deleted": n}


@anvil.server.callable
def export_csv(token, ids=None):
    row = _subscriber(token)
    if row is None:
        return None
    rows = app_tables.links.search(tables.order_by("saved", ascending=False),
                                   email=row["email"])
    links = logic.links_by_ids([_link_dict(r) for r in rows], ids)
    csv_text = logic.links_to_csv(links)
    return anvil.BlobMedia("text/csv", csv_text.encode("utf-8"),
                           name="send2me-links.csv")


def _query_links(row, params):
    filters, err = logic.parse_links_query(params)
    if err:
        return {"ok": False, "error": err}
    result = []
    for link in app_tables.links.search(tables.order_by("saved", ascending=False),
                                        email=row["email"]):
        d = _link_dict(link)
        if logic.link_matches(d, filters):
            result.append((link, d))
    if not filters["keep"]:
        now = datetime.datetime.now()
        for link, d in result:
            link["fetched_at"] = now
    return {"ok": True, "count": len(result),
            "links": [_jsonable(d) for _, d in result]}


@anvil.server.callable
def get_links(token, **params):
    row = _subscriber(token)
    if row is None:
        return {"ok": False, "error": "Unknown key."}
    return _query_links(row, params)


@anvil.server.http_endpoint("/links")
def links_endpoint(**kwargs):
    params = anvil.server.request.query_params
    row = _subscriber(params.get("token"))
    if row is None:
        return _json({"ok": False,
                      "error": "Unknown key. Register at send2me.app."}, 403)
    result = _query_links(row, params)
    return _json(result, 200 if result["ok"] else 400)
