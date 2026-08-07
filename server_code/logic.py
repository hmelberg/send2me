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


ENC_PREFIX = "e1:"


def new_salt():
    """16 tilfeldige bytes som urlsafe-base64 - salt per bruker."""
    try:
        import secrets
        raw = secrets.token_bytes(16)
    except Exception:
        import uuid
        raw = uuid.uuid4().bytes
    return _b64encode(raw)


_SHA256_K = (
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
)

_MASK32 = 0xFFFFFFFF


def _sha256_pure(data):
    """Ren-Python SHA-256 (FIPS 180-4). Ingen imports; kun bytes/int.
    Brukt nar hashlib ikke er tilgjengelig (PyPy-sandboxen)."""
    h0, h1, h2, h3, h4, h5, h6, h7 = (
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
    )
    k = _SHA256_K

    msg = bytearray(data)
    bit_len = len(msg) * 8
    msg.append(0x80)
    while len(msg) % 64 != 56:
        msg.append(0)
    msg += bit_len.to_bytes(8, "big")

    for chunk_start in range(0, len(msg), 64):
        chunk = msg[chunk_start:chunk_start + 64]
        w = [0] * 64
        for i in range(16):
            w[i] = int.from_bytes(chunk[i * 4:i * 4 + 4], "big")
        for i in range(16, 64):
            x15 = w[i - 15]
            s0 = ((x15 >> 7) | (x15 << 25) & _MASK32) ^ \
                 ((x15 >> 18) | (x15 << 14) & _MASK32) ^ \
                 (x15 >> 3)
            x2 = w[i - 2]
            s1 = ((x2 >> 17) | (x2 << 15) & _MASK32) ^ \
                 ((x2 >> 19) | (x2 << 13) & _MASK32) ^ \
                 (x2 >> 10)
            w[i] = (w[i - 16] + s0 + w[i - 7] + s1) & _MASK32

        a, b, c, d, e, f, g, h = h0, h1, h2, h3, h4, h5, h6, h7

        for i in range(64):
            s1 = ((e >> 6) | (e << 26) & _MASK32) ^ \
                 ((e >> 11) | (e << 21) & _MASK32) ^ \
                 ((e >> 25) | (e << 7) & _MASK32)
            ch = (e & f) ^ (~e & g) & _MASK32
            temp1 = (h + s1 + ch + k[i] + w[i]) & _MASK32
            s0 = ((a >> 2) | (a << 30) & _MASK32) ^ \
                 ((a >> 13) | (a << 19) & _MASK32) ^ \
                 ((a >> 22) | (a << 10) & _MASK32)
            maj = (a & b) ^ (a & c) ^ (b & c)
            temp2 = (s0 + maj) & _MASK32

            h = g
            g = f
            f = e
            e = (d + temp1) & _MASK32
            d = c
            c = b
            b = a
            a = (temp1 + temp2) & _MASK32

        h0 = (h0 + a) & _MASK32
        h1 = (h1 + b) & _MASK32
        h2 = (h2 + c) & _MASK32
        h3 = (h3 + d) & _MASK32
        h4 = (h4 + e) & _MASK32
        h5 = (h5 + f) & _MASK32
        h6 = (h6 + g) & _MASK32
        h7 = (h7 + h) & _MASK32

    out = bytearray()
    for part in (h0, h1, h2, h3, h4, h5, h6, h7):
        out += part.to_bytes(4, "big")
    return bytes(out)


def _hmac_sha256_pure(key, msg):
    """Ren-Python HMAC-SHA256 (RFC 2104). Ingen imports."""
    block_size = 64
    if len(key) > block_size:
        key = _sha256_pure(key)
    key = key + b"\x00" * (block_size - len(key))
    ipad = bytes(b ^ 0x36 for b in key)
    opad = bytes(b ^ 0x5C for b in key)
    inner = _sha256_pure(ipad + msg)
    return _sha256_pure(opad + inner)


_B64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


def _b64encode_pure(raw):
    """Ren-Python urlsafe base64-encoding (RFC 4648 sec. 5). Ingen imports."""
    out = []
    n = len(raw)
    i = 0
    while i + 3 <= n:
        b0, b1, b2 = raw[i], raw[i + 1], raw[i + 2]
        val = (b0 << 16) | (b1 << 8) | b2
        out.append(_B64_ALPHABET[(val >> 18) & 0x3F])
        out.append(_B64_ALPHABET[(val >> 12) & 0x3F])
        out.append(_B64_ALPHABET[(val >> 6) & 0x3F])
        out.append(_B64_ALPHABET[val & 0x3F])
        i += 3
    rem = n - i
    if rem == 1:
        b0 = raw[i]
        val = b0 << 16
        out.append(_B64_ALPHABET[(val >> 18) & 0x3F])
        out.append(_B64_ALPHABET[(val >> 12) & 0x3F])
        out.append("==")
    elif rem == 2:
        b0, b1 = raw[i], raw[i + 1]
        val = (b0 << 16) | (b1 << 8)
        out.append(_B64_ALPHABET[(val >> 18) & 0x3F])
        out.append(_B64_ALPHABET[(val >> 12) & 0x3F])
        out.append(_B64_ALPHABET[(val >> 6) & 0x3F])
        out.append("=")
    return "".join(out)


_B64_INDEX = {ch: i for i, ch in enumerate(_B64_ALPHABET)}


def _b64decode_pure(s):
    """Ren-Python urlsafe base64-decoding. Ingen imports."""
    s = s.rstrip("=")
    out = bytearray()
    n = len(s)
    i = 0
    while i + 4 <= n:
        v0 = _B64_INDEX[s[i]]
        v1 = _B64_INDEX[s[i + 1]]
        v2 = _B64_INDEX[s[i + 2]]
        v3 = _B64_INDEX[s[i + 3]]
        val = (v0 << 18) | (v1 << 12) | (v2 << 6) | v3
        out.append((val >> 16) & 0xFF)
        out.append((val >> 8) & 0xFF)
        out.append(val & 0xFF)
        i += 4
    rem = n - i
    if rem == 2:
        v0 = _B64_INDEX[s[i]]
        v1 = _B64_INDEX[s[i + 1]]
        val = (v0 << 18) | (v1 << 12)
        out.append((val >> 16) & 0xFF)
    elif rem == 3:
        v0 = _B64_INDEX[s[i]]
        v1 = _B64_INDEX[s[i + 1]]
        v2 = _B64_INDEX[s[i + 2]]
        val = (v0 << 18) | (v1 << 12) | (v2 << 6)
        out.append((val >> 16) & 0xFF)
        out.append((val >> 8) & 0xFF)
    return bytes(out)


_FORCE_PURE = False  # testene setter True for a tvinge ren-Python-stien

_NATIVE_OK = None


def _native_ok():
    """Sandboxens hashlib-shim kaster Exception ved import - prov en gang."""
    global _NATIVE_OK
    if _NATIVE_OK is None:
        try:
            import hashlib
            import hmac
            hashlib.sha256(b"").digest()
            _NATIVE_OK = True
        except Exception:
            _NATIVE_OK = False
    return _NATIVE_OK


def _sha256(data):
    if not _FORCE_PURE and _native_ok():
        import hashlib
        return hashlib.sha256(data).digest()
    return _sha256_pure(data)


def _hmac_sha256(key, msg):
    if not _FORCE_PURE and _native_ok():
        import hashlib
        import hmac
        return hmac.new(key, msg, hashlib.sha256).digest()
    return _hmac_sha256_pure(key, msg)


def _consteq(a, b):
    if not _FORCE_PURE and _native_ok():
        import hmac
        return hmac.compare_digest(a, b)
    if len(a) != len(b):
        return False
    r = 0
    for x, y in zip(a, b):
        r |= x ^ y
    return r == 0


def _b64encode(raw):
    if not _FORCE_PURE:
        try:
            import base64
            return base64.urlsafe_b64encode(raw).decode("ascii")
        except Exception:
            pass
    return _b64encode_pure(raw)


def _b64decode(s):
    if not _FORCE_PURE:
        try:
            import base64
            return base64.urlsafe_b64decode(s.encode("ascii"))
        except Exception:
            pass
    return _b64decode_pure(s)


def token_hash(token):
    """SHA-256 hex for oppslag. Wrapperen feiler aldri: native hashlib
    brukes nar tilgjengelig, ellers ren-Python-fallback."""
    return _sha256((token or "").encode("utf-8")).hex()


def crypto_available():
    """Sann hvis krypto-stakken gir riktig svar i denne runtimen (native
    hashlib eller ren-Python-fallback)."""
    try:
        expected = bytes.fromhex("5bdcc146bf60754e6a042426089575c7"
                                 "5a003f089d2739839dec58b964ec3843")
        return _hmac_sha256(b"Jefe",
                            b"what do ya want for nothing?") == expected
    except Exception:
        return False


def derive_keys(token, salt_b64):
    """(k_enc, k_mac) fra token + salt. Rask HMAC-avledning er nok fordi
    tokenet kommer fra secrets.token_urlsafe(18), ikke et menneskevalgt
    passord."""
    salt = _b64decode(salt_b64 or "")
    master = _hmac_sha256(salt, (token or "").encode("utf-8"))
    k_enc = _hmac_sha256(master, b"send2me-enc-v1")
    k_mac = _hmac_sha256(master, b"send2me-mac-v1")
    return k_enc, k_mac


def _keystream(k_enc, nonce, n):
    out = b""
    counter = 0
    while len(out) < n:
        out += _hmac_sha256(k_enc, nonce + counter.to_bytes(4, "big"))
        counter += 1
    return out[:n]


def encrypt_value(plain, keys):
    """Str -> 'e1:'-prefikset chiffertekst. Tomme verdier krypteres ogsa,
    sa admin ikke kan se hvilke lenker som har notat/tags."""
    k_enc, k_mac = keys
    try:
        import secrets
        nonce = secrets.token_bytes(16)
    except Exception:
        import uuid
        nonce = uuid.uuid4().bytes
    pt = (plain or "").encode("utf-8")
    ct = bytes(a ^ b for a, b in zip(pt, _keystream(k_enc, nonce, len(pt))))
    tag = _hmac_sha256(k_mac, nonce + ct)[:16]
    return ENC_PREFIX + _b64encode(nonce + ct + tag)


def is_encrypted(value):
    return isinstance(value, str) and value.startswith(ENC_PREFIX)


def decrypt_value(stored, keys):
    """Klartekst, eller None ved feil nokkel, tukling eller ugyldig format.
    Taggen verifiseres FOR dekryptering (encrypt-then-MAC)."""
    if not is_encrypted(stored):
        return None
    k_enc, k_mac = keys
    try:
        raw = _b64decode(stored[len(ENC_PREFIX):])
    except Exception:
        return None
    if len(raw) < 32:
        return None
    nonce, ct, tag = raw[:16], raw[16:-16], raw[-16:]
    want = _hmac_sha256(k_mac, nonce + ct)[:16]
    if not _consteq(tag, want):
        return None
    pt = bytes(a ^ b for a, b in zip(ct, _keystream(k_enc, nonce, len(ct))))
    try:
        return pt.decode("utf-8")
    except UnicodeDecodeError:
        return None


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
        "Want your saved links stored encrypted, so that not even the server\n"
        "admin can read them? Turn on encryption under Settings on your links\n"
        "page. Note: your key then becomes the only way to read them - if you\n"
        "register again and get a new key, previously saved links are deleted.\n\n"
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
