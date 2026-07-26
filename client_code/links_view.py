"""Filtrering og sortering for My links.

Ren logikk uten anvil-avhengigheter, slik at den kan enhetstestes lokalt.
Lenkene kommer fra serveren med `saved` som streng ("YYYY-MM-DD HH:MM").
"""
MAX_STARS = 3

SORT_KEYS = ("saved", "stars", "title")


def stars_of(link):
    """0-3. Serveren har alt loest opp gamle rader uten stars-verdi."""
    n = link.get("stars")
    if n is None:
        return 0
    try:
        n = int(n)
    except (TypeError, ValueError):
        return 0
    return max(0, min(MAX_STARS, n))


def next_stars(current, clicked):
    """Klikk pa stjerne nr `clicked`: sett den verdien, eller nullstill."""
    return 0 if current == clicked else clicked


def day_of(link):
    return (link.get("saved") or "")[:10]


def format_day(day, this_year):
    """Kort dato i lista: MM-DD i ar, full dato ellers."""
    prefix = str(this_year) + "-"
    return day[5:] if day.startswith(prefix) else day


def tags_of(link):
    return [t.strip() for t in (link.get("tags") or "").split(",") if t.strip()]


def all_tags(links):
    seen = {}
    for link in links:
        for tag in tags_of(link):
            seen.setdefault(tag.lower(), tag)
    return [seen[k] for k in sorted(seen)]


def _haystack(link):
    parts = [link.get("title") or "", link.get("url") or "",
             link.get("tags") or "", link.get("note") or ""]
    return " ".join(parts).lower()


def filter_links(links, search="", tag=""):
    query = (search or "").strip().lower()
    want_tag = (tag or "").strip().lower()
    out = []
    for link in links:
        if query and query not in _haystack(link):
            continue
        if want_tag and want_tag not in [t.lower() for t in tags_of(link)]:
            continue
        out.append(link)
    return out


def _sort_key(key):
    if key == "stars":
        return lambda link: (stars_of(link), link.get("saved") or "")
    if key == "title":
        return lambda link: (link.get("title") or link.get("url") or "").lower()
    return lambda link: (link.get("saved") or "")


def sort_links(links, key="saved", descending=True):
    return sorted(links, key=_sort_key(key), reverse=bool(descending))
