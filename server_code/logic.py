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


def registration_email_text(token, js):
    return (
        "Hei!\n\n"
        "Her er din personlige send2me-nøkkel:\n\n"
        "    %s\n\n"
        "Slik kommer du i gang (PC/Mac):\n"
        "1. Gå til https://send2me.app/\n"
        "2. Lim inn nøkkelen i steg 2 og trykk «Lag bokmerke-lenke».\n"
        "3. Dra lenken som dukker opp, til bokmerkelinjen.\n\n"
        "På mobil:\n"
        "1. Lagre en hvilken som helst side som bokmerke, og gi det navnet send2me.\n"
        "2. Rediger bokmerket og erstatt adressen med hele koden under:\n\n"
        "%s\n\n"
        "Deretter: stå på en side, trykk på bokmerket — og lenken ligger i innboksen din.\n\n"
        "Hilsen send2me"
    ) % (token, js)


def sent_page_html():
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>send2me</title></head>"
        "<body style='font-family:sans-serif;text-align:center;"
        "padding-top:1.6em;background:#fafafa'>"
        "<div style='font-size:1.5em'>&#10003; Sendt</div>"
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
