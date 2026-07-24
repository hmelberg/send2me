import datetime

import anvil.email
import anvil.server
import anvil.tables as tables
from anvil.tables import app_tables

import logic


@anvil.server.callable
def register_email(email):
    email_n = logic.normalize_email(email)
    if not logic.valid_email(email_n):
        return {"ok": False, "error": "Ugyldig e-postadresse."}
    today = datetime.date.today()
    row = app_tables.subscribers.get(email=email_n)
    prev_date = row["reg_date"] if row else None
    prev_count = (row["reg_count"] if row else 0) or 0
    count = logic.next_reg_count(prev_date, prev_count, today)
    if count is None:
        return {"ok": False,
                "error": "For mange registreringer i dag. Prøv igjen i morgen."}
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
        subject="Din send2me-nøkkel",
        text=logic.registration_email_text(token, logic.bookmarklet_js(token)))
    return {"ok": True}


@anvil.server.callable
def make_bookmarklet(token):
    token = (token or "").strip()
    row = app_tables.subscribers.get(token=token) if token else None
    if row is None:
        return {"ok": False,
                "error": "Ukjent nøkkel. Sjekk at du limte inn hele nøkkelen fra e-posten."}
    return {"ok": True, "js": logic.bookmarklet_js(token)}


def _html(body, status):
    resp = anvil.server.HttpResponse(status, body)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return resp


@anvil.server.http_endpoint("/sendlink")
def sendlink(**kwargs):
    params = anvil.server.request.query_params
    token = (params.get("token") or "").strip()
    url = params.get("url") or ""
    title = params.get("title") or ""
    row = app_tables.subscribers.get(token=token) if token else None
    if row is None:
        return _html(logic.error_page_html(
            "Ukjent nøkkel. Registrer deg på send2me.app."), 403)
    if not url:
        return _html(logic.error_page_html("Mangler URL."), 400)
    anvil.email.send(
        from_name="send2me", to=row["email"],
        subject=(title or url), text=url)
    return _html(logic.sent_page_html(), 200)
