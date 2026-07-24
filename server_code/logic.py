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
        "Hi!\n\n"
        "Here is your personal send2me key:\n\n"
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
    ) % (token, js)


def sent_page_html():
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>send2me</title></head>"
        "<body style='font-family:sans-serif;text-align:center;"
        "padding-top:1.6em;background:#fafafa'>"
        "<div style='font-size:1.5em'>&#10003; Sent</div>"
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
