"""Ren logikk for send2me - ingen anvil-avhengigheter, testbar lokalt."""
import re

API_BASE = "https://send2me.app/_/api"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_BOOKMARKLET = (
    "javascript:(function(){var u='%s/sendlink?token=%s"
    "&url='+encodeURIComponent(location.href)+"
    "'&title='+encodeURIComponent(document.title);"
    "var w=window.open(u,'send2me','width=220,height=90,"
    "left='+(screen.width-250)+',top='+(screen.height-200));"
    "if(!w){location.href=u;}})()"
)


VALID_MODES = ("email", "save", "both")


def normalize_mode(m):
    return m if m in VALID_MODES else "both"


def normalize_tags(s):
    parts = [p.strip() for p in (s or "").split(",")]
    return ", ".join(p for p in parts if p)


def links_page_url(token, app_base="https://send2me.app"):
    return "%s/#?key=%s" % (app_base, token)


def _flag(v):
    return str(v or "").lower() in ("1", "true", "yes")


def parse_links_query(params):
    """Query-params (dict) -> (filters, None) eller (None, feilmelding)."""
    import datetime as _dt
    f = {"all": _flag(params.get("all")), "keep": _flag(params.get("keep")),
         "since": None, "until": None,
         "tag": (params.get("tag") or "").strip() or None,
         "starred": _flag(params.get("starred"))}
    for name in ("since", "until"):
        raw = str(params.get(name) or "").strip()
        if raw:
            try:
                f[name] = _dt.date(*[int(x) for x in raw.split("-")])
            except (ValueError, TypeError):
                return None, "Invalid %s date, use YYYY-MM-DD." % name
    return f, None


def link_matches(link, filters):
    """link: dict med saved (datetime), fetched_at (datetime|None), tags, starred."""
    if not filters["all"] and link.get("fetched_at") is not None:
        return False
    day = link["saved"].date()
    if filters["since"] and day < filters["since"]:
        return False
    if filters["until"] and day > filters["until"]:
        return False
    if filters["starred"] and not link.get("starred"):
        return False
    if filters["tag"]:
        tags = [t.strip().lower() for t in (link.get("tags") or "").split(",")]
        if filters["tag"].lower() not in tags:
            return False
    return True


def links_to_csv(links):
    import csv
    import io
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["saved", "url", "title", "tags", "note", "starred", "fetched_at"])
    for l in links:
        w.writerow([
            l["saved"].isoformat(sep=" ", timespec="minutes") if l.get("saved") else "",
            l.get("url") or "", l.get("title") or "", l.get("tags") or "",
            l.get("note") or "", "1" if l.get("starred") else "0",
            l["fetched_at"].isoformat(sep=" ", timespec="minutes") if l.get("fetched_at") else "",
        ])
    return out.getvalue()


def normalize_email(s):
    return (s or "").strip().lower()


def valid_email(s):
    return bool(_EMAIL_RE.match(s or ""))


def next_reg_count(prev_date, prev_count, today, limit=3):
    """Ny reg_count for dagens registrering, eller None hvis grensen er nadd."""
    if prev_date != today:
        return 1
    if (prev_count or 0) >= limit:
        return None
    return prev_count + 1


def new_token():
    try:
        import secrets
        return secrets.token_urlsafe(18)
    except Exception:
        import uuid
        return uuid.uuid4().hex


def bookmarklet_js(token, api_base=API_BASE):
    return _BOOKMARKLET % (api_base, token)


def registration_email_text(token, js, links_url):
    return (
        "Hi!\n\n"
        "Here is your personal send2me key:\n\n"
        "    %s\n\n"
        "Your personal links page (open it, then bookmark it or drag it to "
        "your bookmarks bar):\n\n"
        "    %s\n\n"
        "Getting started (computer):\n"
        "1. Go to https://send2me.app/\n"
        "2. Paste the key in step 2 and click \"Create bookmark link\".\n"
        "3. Drag the link that appears to your bookmarks bar.\n\n"
        "On your phone:\n"
        "1. Save any page as a bookmark and name it send2me.\n"
        "2. Edit the bookmark and replace its address with the entire code below:\n\n"
        "%s\n\n"
        "From then on: while on any page, tap the send2me bookmark - "
        "and the link lands in your inbox.\n\n"
        "- send2me"
    ) % (token, links_url, js)


def sent_page_html(label="Sent"):
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>send2me</title></head>"
        "<body style='font-family:sans-serif;text-align:center;"
        "padding-top:1.6em;background:#fafafa'>"
        "<div style='font-size:1.5em'>&#10003; " + label + "</div>"
        "<script>setTimeout(function(){window.close();"
        "if(history.length>1){history.back();}},900);</script>"
        "</body></html>"
    )


def error_page_html(msg):
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>send2me</title></head>"
        "<body style='font-family:sans-serif;text-align:center;"
        "padding-top:1.6em;background:#fafafa'>"
        "<div style='font-size:1.2em'>&#10007; %s</div>"
        "</body></html>"
    ) % msg
