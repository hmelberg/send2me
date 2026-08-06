"""Ren logikk for send2me - ingen anvil-avhengigheter, testbar lokalt."""
import datetime
import re

MAX_LINKS = 1000
RETENTION_MONTHS = 3
_EPOCH = datetime.datetime(1970, 1, 1)

API_BASE = "https://send2me.app/_/api"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_BOOKMARKLET = (
    "javascript:(function(){var u='%s/sendlink?token=%s"
    "&url='+encodeURIComponent(location.href)+"
    "'&title='+encodeURIComponent(document.title);"
    "var w=window.open('','send2me','width=220,height=90,"
    "top=60,left='+(screen.width-250));"
    "if(w){try{w.document.write('Sending...');}catch(e){}"
    "w.location=u;}else{location.href=u;}})()"
)


VALID_MODES = ("email", "save", "both")

MAX_STARS = 3


def normalize_mode(m):
    return m if m in VALID_MODES else "both"


def clamp_stars(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return 0
    return max(0, min(MAX_STARS, n))


def link_stars(stars, starred=False):
    """Kolonneverdi -> 0-3. Rader lagret for stars-kolonna fantes har None,
    og leser den gamle boolske starred som en stjerne."""
    if stars is None:
        return 1 if starred else 0
    return clamp_stars(stars)


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
         "min_stars": 1 if _flag(params.get("starred")) else 0}
    for name in ("since", "until"):
        raw = str(params.get(name) or "").strip()
        if raw:
            try:
                f[name] = _dt.date(*[int(x) for x in raw.split("-")])
            except (ValueError, TypeError):
                return None, "Invalid %s date, use YYYY-MM-DD." % name
    raw_stars = str(params.get("stars") or "").strip()
    if raw_stars:
        try:
            f["min_stars"] = clamp_stars(int(raw_stars))
        except ValueError:
            return None, "Invalid stars, use a number 0-%d." % MAX_STARS
    return f, None


def link_matches(link, filters):
    """link: dict med saved (datetime), fetched_at (datetime|None), tags, stars."""
    if not filters["all"] and link.get("fetched_at") is not None:
        return False
    day = link["saved"].date()
    if filters["since"] and day < filters["since"]:
        return False
    if filters["until"] and day > filters["until"]:
        return False
    if link_stars(link.get("stars"), link.get("starred")) < filters["min_stars"]:
        return False
    if filters["tag"]:
        tags = [t.strip().lower() for t in (link.get("tags") or "").split(",")]
        if filters["tag"].lower() not in tags:
            return False
    return True


def links_over_cap(links, max_links=MAX_LINKS):
    """Ider som ma slettes for at hoyst max_links blir igjen.

    Eldste ryker forst, og stjernemerkede lenker rores bare hvis det ikke er
    nok ustjernede a ta - stjerna er brukerens 'behold denne'."""
    surplus = len(links) - max_links
    if surplus <= 0:
        return []
    by_age = sorted(range(len(links)), key=lambda i: links[i].get("saved") or _EPOCH)
    order = ([i for i in by_age if not links[i].get("stars")]
             + [i for i in by_age if links[i].get("stars")])
    return [links[i]["id"] for i in order[:surplus]]


def links_by_ids(links, ids=None):
    """Tomt/manglende utvalg betyr alle - eksporten uten merkede lenker skal
    virke som for. Eierskapet er alt avgrenset: lista er brukerens egne."""
    if not ids:
        return list(links)
    wanted = set(ids)
    return [l for l in links if l.get("id") in wanted]


def links_to_csv(links):
    import csv
    import io
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["saved", "url", "title", "tags", "note", "stars", "fetched_at"])
    for l in links:
        w.writerow([
            l["saved"].isoformat(sep=" ", timespec="minutes") if l.get("saved") else "",
            l.get("url") or "", l.get("title") or "", l.get("tags") or "",
            l.get("note") or "", link_stars(l.get("stars"), l.get("starred")),
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
        "Your personal send2me key:\n\n"
        "    %s\n\n"
        "Your links page - open it and keep it as a bookmark:\n\n"
        "    %s\n\n"
        "On a computer:\n"
        "1. Go to https://send2me.app/\n"
        "2. Paste the key in step 2 and click \"Create bookmark link\".\n"
        "3. Drag the link that appears to your bookmarks bar.\n"
        "   (On a new machine you can get that link again under Settings\n"
        "   on your links page - no need to dig out this email.)\n\n"
        "On your phone:\n"
        "1. Save any page as a bookmark and name it send2me.\n"
        "2. Edit the bookmark and replace its address with the entire code below:\n\n"
        "%s\n\n"
        "Then just tap the send2me bookmark on any page you want to keep.\n\n"
        "Every link can be emailed to you, saved to My links, or both. Both is\n"
        "the default - change it under Settings on your links page.\n\n"
        "--\n"
        "Small print: send2me is a free hobby service, offered as is. We cannot\n"
        "guarantee that your links stay available, or that the service keeps\n"
        "running. Links older than %d months may be removed, and only your %d\n"
        "most recent links are kept. Use Export CSV on your links page if you\n"
        "want your own copy.\n\n"
        "- send2me"
    ) % (token, links_url, js, RETENTION_MONTHS, MAX_LINKS)


def sent_page_html(label="Sent"):
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>send2me</title></head>"
        "<body style='font-family:sans-serif;text-align:center;"
        "padding-top:1.6em;background:#fafafa'>"
        "<div style='font-size:1.5em'>&#10003; " + label + "</div>"
        "<script>setTimeout(function(){window.close();"
        "if(history.length>1){history.back();}},100);</script>"
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
