# Valgfri kryptering av lagrede lenker — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Brukervalgt kryptering av `url`/`title`/`tags`/`note` (+ `current_tag`) med nøkkel avledet av brukerens token, slik at admin ikke kan lese lagret lenkeinnhold. Spec: `docs/superpowers/specs/2026-08-07-link-encryption-design.md`.

**Architecture:** Rene kryptofunksjoner (stdlib: `hashlib`/`hmac`/`secrets`) i `server_code/logic.py`, testet lokalt. Tynn integrasjon i `server_code/api.py`: felles subscriber-oppslag på token ELLER token-hash, `_enc`/`_dec`-hjelpere rundt alle skrive-/lesestier, migrering på/av i `save_settings`. Sjekkboks i `SettingsForm`. For krypterte brukere lagres aldri tokenet — bare SHA-256-hashen.

**Tech Stack:** Anvil (python3-sandbox — KUN stdlib på server), Anvil Data Tables, unittest lokalt.

## Global Constraints

- Branch: `master`. Committ per task, men **push først i Task 7** (hver push deployer til Anvil).
- Serverkode: ingen eksterne avhengigheter. Følg filens stil med lokale imports inne i funksjoner (`import hashlib` osv. lokalt, som `new_token` gjør med `secrets`).
- Kryptert verdiformat, eksakt: `"e1:" + urlsafe_b64(nonce16 + ct + tag16)`.
- Nøkkelavledning, eksakt: `master = HMAC-SHA256(salt, token_utf8)`; `k_enc = HMAC-SHA256(master, b"send2me-enc-v1")`; `k_mac = HMAC-SHA256(master, b"send2me-mac-v1")`.
- All UI- og e-posttekst på engelsk (matcher eksisterende tekst).
- Rør ikke: `theme/`, `LICENSE.txt`, `.anvil_editor.yaml`, `.gitignore`.
- Testkommando: `python3 -m unittest discover -s tests -v` fra repo-roten. Alle eksisterende tester skal fortsatt passere i hver task.
- `links`-skjemaet i `anvil.yaml` endres IKKE; bare `subscribers` får nye kolonner.

---

### Task 1: Kryptofunksjoner i `logic.py` med tester

**Files:**
- Modify: `server_code/logic.py` (legg til nederst, før `sent_page_html`)
- Test: `tests/test_logic.py` (ny testklasse nederst)

**Interfaces:**
- Consumes: ingenting nytt.
- Produces (brukes av Task 2–5):
  - `logic.ENC_PREFIX` — `"e1:"` (str-konstant)
  - `logic.new_salt() -> str` (urlsafe-b64 av 16 tilfeldige bytes)
  - `logic.token_hash(token: str) -> str` (64 tegn hex)
  - `logic.derive_keys(token: str, salt_b64: str) -> tuple[bytes, bytes]` — `(k_enc, k_mac)`
  - `logic.encrypt_value(plain: str|None, keys: tuple) -> str` — alltid `e1:`-prefikset
  - `logic.decrypt_value(stored: str, keys: tuple) -> str|None` — `None` ved feil nøkkel/tukling/format
  - `logic.is_encrypted(value) -> bool`

- [ ] **Step 1: Skriv failende tester**

Legg til nederst i `tests/test_logic.py`:

```python
class TestCrypto(unittest.TestCase):
    token = "abc123TOKENxyz"

    def setUp(self):
        self.salt = logic.new_salt()
        self.keys = logic.derive_keys(self.token, self.salt)

    def test_roundtrip_unicode(self):
        plain = "https://vg.no/søk?q=blåbær og tittel med æøå"
        enc = logic.encrypt_value(plain, self.keys)
        self.assertTrue(enc.startswith(logic.ENC_PREFIX))
        self.assertNotIn("vg.no", enc)
        self.assertEqual(logic.decrypt_value(enc, self.keys), plain)

    def test_empty_string_roundtrip(self):
        enc = logic.encrypt_value("", self.keys)
        self.assertTrue(logic.is_encrypted(enc))
        self.assertEqual(logic.decrypt_value(enc, self.keys), "")

    def test_none_encrypts_as_empty(self):
        enc = logic.encrypt_value(None, self.keys)
        self.assertEqual(logic.decrypt_value(enc, self.keys), "")

    def test_wrong_token_gives_none(self):
        enc = logic.encrypt_value("hemmelig", self.keys)
        other = logic.derive_keys("feil-token", self.salt)
        self.assertIsNone(logic.decrypt_value(enc, other))

    def test_tampering_gives_none(self):
        import base64
        enc = logic.encrypt_value("hemmelig lenke", self.keys)
        raw = bytearray(base64.urlsafe_b64decode(enc[len(logic.ENC_PREFIX):]))
        raw[20] ^= 0xFF  # flipp en byte i chifferteksten
        tampered = logic.ENC_PREFIX + base64.urlsafe_b64encode(bytes(raw)).decode("ascii")
        self.assertIsNone(logic.decrypt_value(tampered, self.keys))

    def test_garbage_gives_none(self):
        self.assertIsNone(logic.decrypt_value("e1:ikke-base64!!!", self.keys))
        self.assertIsNone(logic.decrypt_value("e1:" , self.keys))
        self.assertIsNone(logic.decrypt_value("https://klartekst.no", self.keys))

    def test_fresh_nonce_gives_distinct_ciphertexts(self):
        a = logic.encrypt_value("samme tekst", self.keys)
        b = logic.encrypt_value("samme tekst", self.keys)
        self.assertNotEqual(a, b)

    def test_is_encrypted(self):
        self.assertTrue(logic.is_encrypted(logic.encrypt_value("x", self.keys)))
        self.assertFalse(logic.is_encrypted("https://vg.no"))
        self.assertFalse(logic.is_encrypted(""))
        self.assertFalse(logic.is_encrypted(None))

    def test_derivation_deterministic(self):
        again = logic.derive_keys(self.token, self.salt)
        self.assertEqual(self.keys, again)
        other_salt = logic.derive_keys(self.token, logic.new_salt())
        self.assertNotEqual(self.keys, other_salt)

    def test_token_hash(self):
        h = logic.token_hash(self.token)
        self.assertEqual(len(h), 64)
        self.assertEqual(h, logic.token_hash(self.token))
        self.assertNotEqual(h, logic.token_hash("annet-token"))

    def test_new_salt_is_16_bytes_and_unique(self):
        import base64
        self.assertEqual(len(base64.urlsafe_b64decode(logic.new_salt())), 16)
        self.assertNotEqual(logic.new_salt(), logic.new_salt())

    def test_long_value_roundtrip(self):
        plain = "x" * 5000  # flere HMAC-blokker i nokkelstrommmen
        enc = logic.encrypt_value(plain, self.keys)
        self.assertEqual(logic.decrypt_value(enc, self.keys), plain)
```

- [ ] **Step 2: Kjør testene og se dem faile**

Run: `python3 -m unittest tests.test_logic.TestCrypto -v` (fra repo-roten)
Expected: FAIL/ERROR med `AttributeError: module 'logic' has no attribute 'new_salt'` e.l.

- [ ] **Step 3: Implementer kryptofunksjonene**

Legg til i `server_code/logic.py`, rett etter `bookmarklet_js` (før `registration_email_text`):

```python
ENC_PREFIX = "e1:"


def new_salt():
    """16 tilfeldige bytes som urlsafe-base64 - salt per bruker."""
    try:
        import secrets
        raw = secrets.token_bytes(16)
    except Exception:
        import uuid
        raw = uuid.uuid4().bytes
    import base64
    return base64.urlsafe_b64encode(raw).decode("ascii")


def token_hash(token):
    """SHA-256 hex for oppslag. Usaltet er OK: tokenet er hoyentropisk."""
    import hashlib
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def derive_keys(token, salt_b64):
    """(k_enc, k_mac) fra token + salt. Rask HMAC-avledning er nok fordi
    tokenet kommer fra secrets.token_urlsafe(18), ikke et menneskevalgt
    passord."""
    import base64
    import hashlib
    import hmac
    salt = base64.urlsafe_b64decode((salt_b64 or "").encode("ascii"))
    master = hmac.new(salt, (token or "").encode("utf-8"), hashlib.sha256).digest()
    k_enc = hmac.new(master, b"send2me-enc-v1", hashlib.sha256).digest()
    k_mac = hmac.new(master, b"send2me-mac-v1", hashlib.sha256).digest()
    return k_enc, k_mac


def _keystream(k_enc, nonce, n):
    import hashlib
    import hmac
    import struct
    out = b""
    counter = 0
    while len(out) < n:
        out += hmac.new(k_enc, nonce + struct.pack(">I", counter),
                        hashlib.sha256).digest()
        counter += 1
    return out[:n]


def encrypt_value(plain, keys):
    """Str -> 'e1:'-prefikset chiffertekst. Tomme verdier krypteres ogsa,
    sa admin ikke kan se hvilke lenker som har notat/tags."""
    import base64
    import hashlib
    import hmac
    k_enc, k_mac = keys
    try:
        import secrets
        nonce = secrets.token_bytes(16)
    except Exception:
        import uuid
        nonce = uuid.uuid4().bytes
    pt = (plain or "").encode("utf-8")
    ct = bytes(a ^ b for a, b in zip(pt, _keystream(k_enc, nonce, len(pt))))
    tag = hmac.new(k_mac, nonce + ct, hashlib.sha256).digest()[:16]
    return ENC_PREFIX + base64.urlsafe_b64encode(nonce + ct + tag).decode("ascii")


def is_encrypted(value):
    return isinstance(value, str) and value.startswith(ENC_PREFIX)


def decrypt_value(stored, keys):
    """Klartekst, eller None ved feil nokkel, tukling eller ugyldig format.
    Taggen verifiseres FOR dekryptering (encrypt-then-MAC)."""
    import base64
    import hashlib
    import hmac
    if not is_encrypted(stored):
        return None
    k_enc, k_mac = keys
    try:
        raw = base64.urlsafe_b64decode(stored[len(ENC_PREFIX):].encode("ascii"))
    except Exception:
        return None
    if len(raw) < 32:
        return None
    nonce, ct, tag = raw[:16], raw[16:-16], raw[-16:]
    want = hmac.new(k_mac, nonce + ct, hashlib.sha256).digest()[:16]
    if not hmac.compare_digest(tag, want):
        return None
    pt = bytes(a ^ b for a, b in zip(ct, _keystream(k_enc, nonce, len(ct))))
    try:
        return pt.decode("utf-8")
    except UnicodeDecodeError:
        return None
```

- [ ] **Step 4: Kjør alle testene**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS, inkludert alle 13 nye i `TestCrypto`.

- [ ] **Step 5: Commit**

```bash
git add server_code/logic.py tests/test_logic.py
git commit -m "feat: stdlib-kryptoprimitiver for lenkekryptering (e1-format)"
```

---

### Task 2: Skjema i `anvil.yaml` + felles subscriber-oppslag i `api.py`

**Files:**
- Modify: `anvil.yaml` (subscribers-kolonner)
- Modify: `server_code/api.py:13-15` (`_subscriber`), `api.py:73-81` (`make_bookmarklet`)

**Interfaces:**
- Consumes: `logic.token_hash`, `logic.derive_keys` (Task 1).
- Produces (brukes av Task 3–5):
  - `_subscriber(token) -> row|None` — finner rad på `token` ELLER `token_hash`.
  - `_sub_keys(row, token) -> tuple|None` — nøkkelpar hvis `row["enc"]`, ellers `None`.

- [ ] **Step 1: Nye kolonner i `anvil.yaml`**

I `db_schema.subscribers.columns`, legg til etter `current_tag`-kolonnen:

```yaml
    - admin_ui: {width: 60}
      name: enc
      type: bool
    - admin_ui: {width: 150}
      name: enc_salt
      type: string
    - admin_ui: {width: 200}
      name: token_hash
      type: string
```

- [ ] **Step 2: Utvid `_subscriber` og legg til `_sub_keys`**

Erstatt hele `_subscriber` i `api.py` (linje 13–15) med:

```python
def _subscriber(token):
    """Finner raden pa klartekst-token eller (for krypterte brukere) pa
    SHA-256-hashen - selve tokenet lagres ikke nar kryptering er pa."""
    token = (token or "").strip()
    if not token:
        return None
    row = app_tables.subscribers.get(token=token)
    if row is None:
        row = app_tables.subscribers.get(token_hash=logic.token_hash(token))
    return row


def _sub_keys(row, token):
    """Nokkelpar for kryptert bruker, ellers None (klartekst-modus)."""
    if row is not None and row["enc"]:
        return logic.derive_keys((token or "").strip(), row["enc_salt"])
    return None
```

- [ ] **Step 3: `make_bookmarklet` over på fellesoppslaget**

I `make_bookmarklet` (api.py:73-81), erstatt de to første linjene i funksjonskroppen:

```python
    token = (token or "").strip()
    row = app_tables.subscribers.get(token=token) if token else None
```

med:

```python
    token = (token or "").strip()
    row = _subscriber(token)
```

(Bookmarkleten bygges fortsatt av rå-tokenet fra brukerens input — riktig, det er det som skal stå i bokmerket.)

- [ ] **Step 4: Kjør testene (regresjon)**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS (api.py testes ikke lokalt, men logic-testene skal være grønne).

- [ ] **Step 5: Commit**

```bash
git add anvil.yaml server_code/api.py
git commit -m "feat: token_hash-oppslag og nokkelavledning for krypterte brukere"
```

---

### Task 3: Kryptert skriving og lesing av lenker i `api.py`

**Files:**
- Modify: `server_code/api.py` — `_link_dict` (18–22), `sendlink` (101–124), `get_settings` (127–134), `get_my_links` (152–159), `_own_link` (162–169), `update_link` (172–185), `export_csv` (209–219), `_query_links` (222–237), `get_links` (240–245), `links_endpoint` (248–256). (Linjenumre er før Task 2-endringene — bruk funksjonsnavn.)

**Interfaces:**
- Consumes: `_subscriber`, `_sub_keys` (Task 2); `logic.encrypt_value`, `logic.decrypt_value`, `logic.is_encrypted` (Task 1).
- Produces (brukes av Task 4 og 6):
  - `_enc(value, keys) -> str` og `_dec(value, keys) -> str|None`
  - `_link_dict(row, keys=None)` — dekrypterer feltene
  - `_query_links(row, keys, params)` — ny signatur med `keys`
  - `_own_link(token, link_id) -> (link|None, keys|None)` — NY returtype (tuple)
  - `get_settings` returnerer i tillegg `"encrypted": bool`

- [ ] **Step 1: Legg til `_enc`/`_dec` og utvid `_link_dict`**

Rett over `_link_dict`, legg til:

```python
def _enc(value, keys):
    return logic.encrypt_value(value, keys) if keys else (value or "")


def _dec(value, keys):
    """Dekrypterer hvis feltet er kryptert og vi har nokler. Rader som ikke
    lar seg dekryptere vises som markor i stedet for a krasje."""
    if keys and logic.is_encrypted(value or ""):
        plain = logic.decrypt_value(value, keys)
        return "[unreadable]" if plain is None else plain
    return value
```

Erstatt `_link_dict` med:

```python
def _link_dict(row, keys=None):
    return {"id": row.get_id(), "url": _dec(row["url"], keys),
            "title": _dec(row["title"], keys),
            "saved": row["saved"], "fetched_at": row["fetched_at"],
            "tags": _dec(row["tags"], keys) or "",
            "note": _dec(row["note"], keys) or "",
            "stars": logic.link_stars(row["stars"], row["starred"])}
```

- [ ] **Step 2: `sendlink` krypterer ved lagring**

I `sendlink`, etter `row = _subscriber(...)`-sjekkene og `mode`-linjen, erstatt `add_row`-blokken:

```python
    mode = logic.normalize_mode(row["mode"])
    keys = _sub_keys(row, params.get("token"))
    if mode != "email":
        tags = logic.normalize_tags(_dec(row["current_tag"], keys))
        app_tables.links.add_row(
            email=row["email"], url=_enc(url, keys), title=_enc(title, keys),
            saved=datetime.datetime.now(), fetched_at=None,
            tags=_enc(tags, keys),
            note=_enc("", keys), stars=0, starred=False)
        _enforce_cap(row["email"])
```

(E-postdelen under er uendret — klarteksten `url`/`title` står i selve forespørselen.)

- [ ] **Step 3: `get_settings` dekrypterer og rapporterer status**

Erstatt `get_settings` med:

```python
@anvil.server.callable
def get_settings(token):
    row = _subscriber(token)
    if row is None:
        return {"ok": False, "error": "Unknown key."}
    keys = _sub_keys(row, token)
    return {"ok": True, "email": row["email"],
            "mode": logic.normalize_mode(row["mode"]),
            "current_tag": _dec(row["current_tag"], keys) or "",
            "encrypted": bool(row["enc"])}
```

- [ ] **Step 4: Lesestiene dekrypterer**

`get_my_links` — hent nøkler og send dem inn:

```python
@anvil.server.callable
def get_my_links(token):
    row = _subscriber(token)
    if row is None:
        return {"ok": False, "error": "Unknown key."}
    keys = _sub_keys(row, token)
    rows = app_tables.links.search(tables.order_by("saved", ascending=False),
                                   email=row["email"])
    return {"ok": True, "links": [_jsonable(_link_dict(r, keys)) for r in rows]}
```

`_own_link` — returner nøklene sammen med lenka (NY returtype, tuple):

```python
def _own_link(token, link_id):
    row = _subscriber(token)
    if row is None:
        return None, None
    link = app_tables.links.get_by_id(link_id)
    if link is None or link["email"] != row["email"]:
        return None, None
    return link, _sub_keys(row, token)
```

`update_link` — krypter nye verdier, returner klartekst:

```python
@anvil.server.callable
def update_link(token, link_id, tags=None, note=None, stars=None):
    link, keys = _own_link(token, link_id)
    if link is None:
        return {"ok": False, "error": "Not found."}
    if tags is not None:
        clean = logic.normalize_tags(tags)
        link["tags"] = _enc(clean, keys)
    if note is not None:
        link["note"] = _enc((note or "").strip(), keys)
    if stars is not None:
        n = logic.clamp_stars(stars)
        link.update(stars=n, starred=n > 0)
    return {"ok": True, "tags": _dec(link["tags"], keys) or "",
            "stars": logic.link_stars(link["stars"], link["starred"])}
```

`delete_link` — tilpass til ny `_own_link`-signatur:

```python
@anvil.server.callable
def delete_link(token, link_id):
    link, _keys = _own_link(token, link_id)
    if link is None:
        return {"ok": False, "error": "Not found."}
    link.delete()
    return {"ok": True}
```

`export_csv` — nøkler inn i `_link_dict`:

```python
    keys = _sub_keys(row, token)
    rows = app_tables.links.search(tables.order_by("saved", ascending=False),
                                   email=row["email"])
    links = logic.links_by_ids([_link_dict(r, keys) for r in rows], ids)
```

`_query_links` — ny signatur `(row, keys, params)`; eneste endring i kroppen er
`d = _link_dict(link, keys)`. Oppdater kallene:
- i `get_links`: `keys = _sub_keys(row, token)` og `return _query_links(row, keys, params)`
- i `links_endpoint`: `keys = _sub_keys(row, params.get("token"))` og `result = _query_links(row, keys, params)`

- [ ] **Step 5: Kjør testene (regresjon) og les gjennom diffen**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS.
Sjekk med `git diff server_code/api.py` at INGEN kodesti skriver klartekst når `keys` er satt: `add_row` i `sendlink`, `link["tags"]`/`link["note"]` i `update_link`.

- [ ] **Step 6: Commit**

```bash
git add server_code/api.py
git commit -m "feat: krypter/dekrypter lenkefelter i alle skrive- og lesestier"
```

---

### Task 4: `save_settings` — slå kryptering på/av med migrering

**Files:**
- Modify: `server_code/api.py` — `save_settings` (og to nye hjelpere rett over)

**Interfaces:**
- Consumes: `_subscriber`, `_sub_keys`, `_enc`, `_dec` (Task 2–3); `logic.new_salt`, `logic.token_hash`, `logic.derive_keys` (Task 1).
- Produces (brukes av Task 6): `save_settings(token, mode=None, current_tag=None, encrypt=None)` — returnerer i tillegg `"encrypted": bool` og `"migrated": int|None`.

- [ ] **Step 1: Hjelpere for migrering**

Rett over `save_settings`, legg til:

```python
def _enable_encryption(row, token):
    """Krypterer alle brukerens rader, bytter lagret token med hash.
    Returnerer (keys, antall_migrerte)."""
    salt = logic.new_salt()
    keys = logic.derive_keys(token, salt)
    n = 0
    for link in app_tables.links.search(email=row["email"]):
        link.update(url=_enc(link["url"] or "", keys),
                    title=_enc(link["title"] or "", keys),
                    tags=_enc(link["tags"] or "", keys),
                    note=_enc(link["note"] or "", keys))
        n += 1
    row.update(enc=True, enc_salt=salt,
               token_hash=logic.token_hash(token), token=None,
               current_tag=_enc(row["current_tag"] or "", keys))
    return keys, n


def _disable_encryption(row, token, keys):
    """Dekrypterer alt tilbake til klartekst. Returnerer (None, antall)."""
    n = 0
    for link in app_tables.links.search(email=row["email"]):
        link.update(url=_dec(link["url"], keys) or "",
                    title=_dec(link["title"], keys) or "",
                    tags=_dec(link["tags"], keys) or "",
                    note=_dec(link["note"], keys) or "")
        n += 1
    row.update(enc=False, enc_salt=None, token_hash=None, token=token,
               current_tag=_dec(row["current_tag"], keys) or "")
    return None, n
```

- [ ] **Step 2: Utvid `save_settings`**

Erstatt hele `save_settings` med:

```python
@anvil.server.callable
def save_settings(token, mode=None, current_tag=None, encrypt=None):
    """Bare feltene som sendes inn endres - modus bor i innstillings-modalen,
    current tag i overskriften, og de lagrer seg hver for seg.
    encrypt=True/False migrerer alle brukerens rader i samme kall."""
    token = (token or "").strip()
    row = _subscriber(token)
    if row is None:
        return {"ok": False, "error": "Unknown key."}
    keys = _sub_keys(row, token)
    migrated = None
    if encrypt is not None and bool(encrypt) != bool(row["enc"]):
        if encrypt:
            keys, migrated = _enable_encryption(row, token)
        else:
            keys, migrated = _disable_encryption(row, token, keys)
    if mode is not None:
        row["mode"] = logic.normalize_mode(mode)
    if current_tag is not None:
        row["current_tag"] = _enc(logic.normalize_tags(current_tag), keys)
    return {"ok": True, "mode": logic.normalize_mode(row["mode"]),
            "current_tag": _dec(row["current_tag"], keys) or "",
            "encrypted": bool(row["enc"]), "migrated": migrated}
```

- [ ] **Step 3: Kjør testene (regresjon)**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add server_code/api.py
git commit -m "feat: sla kryptering pa/av i save_settings med full migrering"
```

---

### Task 5: `register_email` for krypterte brukere + nytt e-postavsnitt

**Files:**
- Modify: `server_code/logic.py` — `registration_email_text`
- Modify: `server_code/api.py` — `register_email`
- Test: `tests/test_logic.py`

**Interfaces:**
- Consumes: `logic.new_salt`, `logic.token_hash` (Task 1).
- Produces: ingenting nytt for senere tasks.

- [ ] **Step 1: Failende test for e-postteksten**

Legg til i `tests/test_logic.py` (det finnes trolig en eksisterende testklasse for e-postteksten — legg metoden der, ellers ny klasse):

```python
class TestRegistrationEmailEncryption(unittest.TestCase):
    def test_mentions_encryption_option(self):
        text = logic.registration_email_text("TOK", "javascript:x", "https://send2me.app/#?key=TOK")
        self.assertIn("Turn on encryption under Settings", text)
        self.assertIn("previously saved links are deleted", text)
        # avsnittet skal sta for "Small print"
        self.assertLess(text.index("Turn on encryption"), text.index("Small print"))
```

- [ ] **Step 2: Kjør testen og se den faile**

Run: `python3 -m unittest tests.test_logic.TestRegistrationEmailEncryption -v`
Expected: FAIL (`AssertionError: 'Turn on encryption under Settings' not found ...`)

- [ ] **Step 3: Nytt avsnitt i `registration_email_text`**

I `logic.registration_email_text`, rett etter avsnittet som slutter med
`"the default - change it under Settings on your links page.\n\n"`, legg til:

```python
        "Want your saved links stored encrypted, so that not even the server\n"
        "admin can read them? Turn on encryption under Settings on your links\n"
        "page. Note: your key then becomes the only way to read them - if you\n"
        "register again and get a new key, previously saved links are deleted.\n\n"
```

- [ ] **Step 4: Kjør testen igjen**

Run: `python3 -m unittest tests.test_logic -v`
Expected: PASS (alle, inkludert eksisterende e-posttester).

- [ ] **Step 5: `register_email` håndterer kryptert bruker**

I `api.py`, i `register_email`, erstatt:

```python
    token = logic.new_token()
    if row:
        row.update(token=token, reg_date=today, reg_count=count)
```

med:

```python
    token = logic.new_token()
    if row:
        if row["enc"]:
            # Nytt token = ny nokkel: gamle krypterte rader er ugjenkallelig
            # uleselige, sa de slettes (jf. spec). Kryptering forblir pa.
            for link in app_tables.links.search(email=email_n):
                link.delete()
            row.update(token=None, token_hash=logic.token_hash(token),
                       enc_salt=logic.new_salt(), current_tag=None,
                       reg_date=today, reg_count=count)
        else:
            row.update(token=token, reg_date=today, reg_count=count)
```

- [ ] **Step 6: Kjør alle testene og commit**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS.

```bash
git add server_code/logic.py server_code/api.py tests/test_logic.py
git commit -m "feat: re-registrering for krypterte brukere + kryptering nevnt i eposten"
```

---

### Task 6: Sjekkboks i `SettingsForm`

**Files:**
- Modify: `client_code/SettingsForm/form_template.yaml`
- Modify: `client_code/SettingsForm/__init__.py`

**Interfaces:**
- Consumes: `get_settings` med `"encrypted"` (Task 3); `save_settings(..., encrypt=...)` med `"migrated"` (Task 4).
- Produces: ingenting for senere tasks.

- [ ] **Step 1: Komponent i `form_template.yaml`**

Rett etter `mode_panel`-blokken (etter linjen `type: FlowPanel` som avslutter den), legg til:

```yaml
- components:
  - event_bindings: {change: encrypt_changed}
    layout_properties: {}
    name: check_encrypt
    properties: {text: Encrypt my saved links}
    type: CheckBox
  - layout_properties: {}
    name: label_encrypt_hint
    properties: {role: settings-hint, text: 'Not even the admin can read them'}
    type: Label
  layout_properties: {}
  name: encrypt_panel
  properties: {role: settings-row}
  type: FlowPanel
```

- [ ] **Step 2: Init + handler i `__init__.py`**

I `__init__`, rett etter `self.saved_mode = settings["mode"]`, legg til:

```python
        self.check_encrypt.checked = bool(settings.get("encrypted"))
```

Etter `mode_changed`-metoden, legg til:

```python
    def encrypt_changed(self, **event_args):
        turn_on = self.check_encrypt.checked
        if turn_on:
            ok = confirm("Encrypt your saved links?\n\n"
                         "Your key becomes the only way to read them. If you "
                         "lose it and register again, your saved links will "
                         "be deleted. Export CSV first if you want a plain copy.",
                         dismissible=True,
                         buttons=[("Encrypt my links", True), ("Cancel", False)])
        else:
            ok = confirm("Turn off encryption?\n\n"
                         "Your saved links will be stored as plain text again.",
                         dismissible=True,
                         buttons=[("Turn off", True), ("Cancel", False)])
        if not ok:
            self.check_encrypt.checked = not turn_on
            return
        result = anvil.server.call('save_settings', self.key, encrypt=turn_on)
        if result["ok"]:
            if turn_on:
                self._status("Encrypted %d links." % (result.get("migrated") or 0))
            else:
                self._status("Encryption turned off.")
        else:
            self.check_encrypt.checked = not turn_on
            self._status(result["error"])
```

- [ ] **Step 3: Kjør testene (regresjon) og commit**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS (klientkoden testes ikke lokalt).

```bash
git add client_code/SettingsForm/form_template.yaml client_code/SettingsForm/__init__.py
git commit -m "feat: krypteringsvalg med bekreftelsesdialog i innstillingene"
```

---

### Task 7: Deploy, sandbox-selvtest og manuell E2E-verifisering

**Files:**
- Modify (midlertidig): `server_code/api.py` — selvtest-endepunkt som fjernes igjen

**Interfaces:**
- Consumes: alt over.
- Produces: verifisert deploy.

- [ ] **Step 1: Midlertidig selvtest-endepunkt**

Nederst i `api.py`, legg til:

```python
@anvil.server.http_endpoint("/enc_selftest")
def enc_selftest(**kwargs):
    """MIDLERTIDIG: bekrefter at hashlib/hmac virker i python3-sandbox.
    Fjernes etter verifisering."""
    salt = logic.new_salt()
    keys = logic.derive_keys("selftest-token", salt)
    enc = logic.encrypt_value("hello æøå", keys)
    ok = (logic.decrypt_value(enc, keys) == "hello æøå"
          and logic.decrypt_value(enc, logic.derive_keys("x", salt)) is None)
    return _json({"ok": ok}, 200)
```

```bash
git add server_code/api.py
git commit -m "chore: midlertidig kryptoselvtest-endepunkt"
```

- [ ] **Step 2: Push (deployer alle tasks) og kjør selvtesten**

```bash
git push
sleep 20  # gi Anvil tid til å deploye
curl -s https://send2me.app/_/api/enc_selftest
```

Expected: `{"ok": true}`. Hvis 500/ImportError: sandboxen mangler `hashlib`/`hmac` — STOPP og rapporter; da må runtime-oppgradering (Python 3.10-miljø) vurderes før videre arbeid.

- [ ] **Step 3: Manuell E2E-sjekkliste (mot live-appen)**

1. Registrer en testadresse på https://send2me.app/ og hent tokenet fra e-posten. Sjekk at e-posten nevner «Turn on encryption under Settings».
2. Lagre en lenke: åpne `https://send2me.app/_/api/sendlink?token=<TOKEN>&url=https://example.com/hemmelig&title=Hemmelig+side` — forvent «Sent/Saved»-kvittering.
3. Åpne lenkesiden (`https://send2me.app/#?key=<TOKEN>`) → Settings → huk av «Encrypt my saved links» → bekreft. Forvent status «Encrypted 1 links.»
4. I Anvil-editorens Data Tables: `links`-raden viser `e1:...` i `url`/`title`/`tags`/`note`; `subscribers`-raden har `token` tom, `token_hash` satt, `enc` = true.
5. Lenkesiden viser fortsatt klartekst; lagre en NY lenke via bookmarklet-URL-en — vises i klartekst på siden, `e1:` i tabellen.
6. Export CSV → klartekst i fila. Tag-filter/søk på siden virker.
7. Settings → hent bookmarkleten på nytt (fungerer = hash-oppslaget virker).
8. Slå AV kryptering → tabellen viser klartekst igjen, `token` tilbake, `token_hash` tom.
9. Slå PÅ igjen, og re-registrer samme adresse → gamle lenker slettet, `enc` fortsatt true, nytt `token_hash`.

- [ ] **Step 4: Fjern selvtesten og push**

Slett `enc_selftest`-funksjonen fra `api.py`.

```bash
git add server_code/api.py
git commit -m "chore: fjern kryptoselvtest-endepunktet"
git push
```

- [ ] **Step 5: Sluttsjekk**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS. Kjør så en siste `curl -s https://send2me.app/_/api/enc_selftest` — forvent 404 (fjernet).
