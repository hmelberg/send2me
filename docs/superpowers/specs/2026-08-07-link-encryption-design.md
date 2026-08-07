# send2me: Valgfri kryptering av lagrede lenker — design

**Dato:** 2026-08-07
**Status:** Godkjent retning (opsjon B — nøkkel avledet av brukerens token), detaljert her.

## Mål

En bruker skal kunne slå på kryptering under Settings på lenkesiden sin, slik at
`url`, `title`, `tags` og `note` (og `current_tag` i innstillingene) lagres som
chiffertekst i Anvil Data Tables. Admin (appeier i tabell-editoren, eller noen
med en database-dump) skal ikke kunne lese *hva* brukeren har lagret — bare
*hvem* (e-post), *når* (tidsstempler) og *hvor mye* (antall rader, stjerner).

## Trusselmodell — hva dette beskytter mot, og ikke

Beskytter mot:
- Admin som blar i Data Tables-editoren og leser brukernes lenker.
- Lekkasje/dump av databasen: lenkeinnhold er chiffertekst, og tokens finnes
  bare som SHA-256-hasher, så nøklene kan ikke avledes fra dumpen.

Beskytter ikke mot (bevisste avgrensninger, ikke mangler):
- En ondsinnet operatør som endrer serverkoden til å logge tokens idet de
  kommer inn. All server-side dekryptering har denne grensen; ekte E2E ble
  vurdert og forkastet (bryter e-postmodus og serversøk, og webappens JS
  serveres uansett fra samme server).
- Metadata: e-postadresse, tidsstempler, antall lenker, stjerner og modus
  forblir synlige.
- Innhold i selve e-postene (e-postmodus sender URL-en i klartekst per
  e-postens natur).
- Lengder: chifferteksten er like lang som klarteksten, så admin ser hvor
  lang en URL/tittel er og om et notat- eller tag-felt er tomt (innholdet
  forblir skjult).

## Nøkkelidé

Tokenet følger med hver eneste forespørsel (`_subscriber(token)` i `api.py`).
Serveren trenger derfor aldri å *lagre* tokenet for å kunne dekryptere — den
avleder nøkkelen fra tokenet i minnet under kallet. For krypterte brukere
lagres bare `token_hash` (SHA-256) for oppslag. Mister brukeren tokenet, er
dataene ugjenkallelig tapt — det er selve garantien, og brukeren advares
eksplisitt i UI og e-post.

## Datamodell (`anvil.yaml`, kun `subscribers` endres)

Nye kolonner i `subscribers`:
- `enc` (bool) — kryptering på/av.
- `enc_salt` (string) — 16 tilfeldige bytes, urlsafe-base64. Nytt salt hver
  gang kryptering slås på.
- `token_hash` (string) — SHA-256 hex av tokenet. Satt når `enc` er på; da er
  `token` satt til `None`. Når `enc` er av: `token` i klartekst, `token_hash`
  er `None` (som i dag).

`links`-skjemaet er uendret: krypterte verdier lagres i de eksisterende
strengkolonnene med prefiks `e1:` (selvbeskrivende og versjonert — primitivet
kan byttes til AES-GCM som `e2:` hvis runtime senere oppgraderes fra
python3-sandbox). `email`, `saved`, `fetched_at`, `stars`, `starred` forblir
klartekst (trengs for utsending, sortering og 1000-lenkers-taket).

## Kryptoskjema v1 (ren stdlib: `hashlib`, `hmac`, `secrets`)

Sandbox-runtimen har ikke `cryptography`-pakken, så v1 bygges av
standardprimitiver på lærebokvis (PRF-basert strømchiffer + encrypt-then-MAC):

- Nøkkelavledning: `master = HMAC-SHA256(key=salt, msg=token_utf8)`;
  `k_enc = HMAC-SHA256(master, b"send2me-enc-v1")`;
  `k_mac = HMAC-SHA256(master, b"send2me-mac-v1")`.
  (Tokenet har ~144 bits entropi fra `secrets.token_urlsafe(18)`, så rask
  avledning er riktig — ingen grunn til PBKDF2.)
- Kryptering av én verdi: `nonce` = 16 tilfeldige bytes; nøkkelstrøm i blokker
  `HMAC-SHA256(k_enc, nonce + teller_be32)`; chiffertekst = klartekst (utf-8)
  XOR nøkkelstrøm; `tag = HMAC-SHA256(k_mac, nonce + ct)[:16]`.
  Lagret verdi: `"e1:" + urlsafe_b64(nonce + ct + tag)`.
- Dekryptering: verifiser tag med `hmac.compare_digest` FØR dekryptering;
  ved feil returneres `None`, og lesestiene viser `"[unreadable]"` i stedet
  for å krasje. (Skal ikke forekomme i praksis pga. slette-regelen under.)
- Tomme strenger krypteres også — uniform behandling, så admin ikke kan se
  hvilke lenker som har notat/tags.
- `token_hash = SHA-256-hex(token_utf8)` — usaltet er OK fordi tokenet er
  høyentropisk (ikke et menneskevalgt passord).

Alle kryptofunksjonene er rene funksjoner i `logic.py` (ingen anvil-importer),
testbare lokalt med unittest, etter repoets etablerte mønster.

## Serverendringer (`api.py`)

- `_subscriber(token)`: slår opp på `token` først, deretter `token_hash`
  (to `get`-kall, begge indekserbare oppslag). En liten hjelper gir
  `(row, key)` der `key` er avledet når `row["enc"]`, ellers `None`.
  `make_bookmarklet` gjør i dag sitt eget `get(token=...)`-oppslag og MÅ over
  på `_subscriber`, ellers låses krypterte brukere ute av bookmark-gjenhenting.
- `sendlink`: hvis kryptering på — dekrypter `current_tag` fra subscriber-raden
  før `normalize_tags`, og krypter `url`, `title`, `tags` før `add_row`.
  E-postmodus uendret (klarteksten står i selve forespørselen).
- Lesestier (`get_my_links`, `_query_links`, `export_csv`): dekrypter feltene
  per rad før `_link_dict`/filtrering — søk, tags-filter og CSV virker som før
  og returnerer klartekst til brukeren.
- `update_link`: krypter nye `tags`/`note` før lagring når kryptering er på.
- `_enforce_cap`: urørt (bruker bare `saved`/`stars`).
- `get_settings`: returnerer i tillegg `"encrypted": bool`; `current_tag`
  dekrypteres før retur.
- `save_settings(token, mode, current_tag, encrypt)`:
  - Når kryptering er på: innkommende `current_tag` normaliseres og krypteres
    før lagring; returverdiene er alltid klartekst.
  - `encrypt=True`: generer salt, krypter alle eksisterende lenkerader
    (inkl. `current_tag` i subscriber-raden), sett `enc=True`,
    `token_hash=hash(token)`, `token=None`. Returner antall migrerte.
  - `encrypt=False`: dekrypter alle rader tilbake til klartekst, sett
    `enc=False`, `token=token` (fra forespørselen), `token_hash=None`.
  - Migreringen skjer i ett serverkall (maks 1000 rader; HMAC er billig,
    radoppdateringene er kostnaden — antas OK innenfor sandboxens
    tidsgrense, verifiseres i implementasjonen).
- `register_email`: hvis eksisterende rad har `enc=True` — lagre bare
  `pending_hash` og la lenker og gjeldende nøkkel være i fred; slettingen
  skjer først når den nye nøkkelen brukes. Se «Re-registrering: ventende
  nøkkel» under for hvorfor.

## UI (`SettingsForm`)

Sjekkboks «Encrypt my saved links» med kort hint-tekst, under modus-valget.
Ved endring en bekreftelsesdialog i samme stil som «Delete ALL»:

- Slå på: «Encrypt your saved links?\n\nYour key becomes the only way to read
  them. If you lose it and register again, your saved links will be deleted.
  Export CSV first if you want a plain copy.»
- Slå av: «Turn off encryption?\n\nYour saved links will be stored as plain
  text again.»

Avbrytes dialogen, settes sjekkboksen tilbake. Etterpå vises status
(«Encrypted N links.» / «Encryption turned off.»).

## Registrerings-e-posten (`logic.registration_email_text`)

Nytt avsnitt (før «Small print»), på engelsk som resten av e-posten:

> Want your saved links stored encrypted, so that not even the server admin
> can read them? Turn on encryption under Settings on your links page.
> Note: your key then becomes the only way to read them — if you register
> again and get a new key, previously saved links are deleted.

## Re-registrering: ventende nøkkel

`register_email` krever bare en e-postadresse, så den kan ikke få lov til å
slette et kryptert arkiv direkte. Ved re-registrering av en kryptert bruker
lagres bare hashen av det nye tokenet i `pending_hash`; verken lenker eller
gjeldende nøkkel røres. Først når noen faktisk bruker den nye nøkkelen —
altså har lest postkassa — slettes de gamle (uleselige) radene, og den nye
nøkkelen tas i bruk. En ubrukt ventende rotasjon ryddes bort ved neste
ikke-krypterte registrering eller ved av-slåing av kryptering.

Kjente, aksepterte begrensninger:

- Blir en aktivering avbrutt (salt lagret, `enc` ennå ikke satt), går en
  re-registrering på det tidspunktet gjennom den ikke-krypterte grenen og
  nullstiller saltet — de radene som rakk å bli kryptert blir da uleselige.
  Vinduet er svært smalt (krever timeout midt i migreringen), og brukeren kan
  slette radene selv. Å slå kryptering på igjen fullfører en avbrutt
  aktivering; å slå den av ruller den tilbake.
- Anvil har ingen transaksjoner, så en migrering av mange rader er ikke
  atomisk. Den er til gjengjeld gjenopptakbar: saltet lagres først, allerede
  krypterte felter hoppes over, og `enc` settes til slutt.
- `migrated`-tallet i svaret teller bare raden i det kallet, så det
  underrapporterer etter en gjenopptatt migrering.

## Testing

- `tests/test_logic.py` (unittest, som i dag): rundtur (krypter → dekrypter),
  unicode og tomme strenger, feil token gir `None`, tuklet chiffertekst gir
  `None`, to krypteringer av samme verdi gir ulik chiffertekst (nonce),
  `e1:`-prefiksdeteksjon, nøkkelavledning er deterministisk for samme
  token+salt.
- Verifikasjonssteg i implementasjonen: bekreft at `hashlib`/`hmac` importerer
  og kjører i python3-sandbox-runtimen (midlertidig selvtest-callable ved
  første deploy; `new_token` sin try/except rundt `secrets` viser at sandboxen
  kan være kresen på importer).
- Testkommando: `python3 -m unittest discover -s tests -v` fra repo-roten.

## Ikke-mål

- Ende-til-ende-kryptering i nettleseren.
- Skjuling av metadata (e-post, tidsstempler, antall, stjerner, modus).
- Kryptering for brukere som ikke aktivt slår det på (standard er av).
- Hashing av tokens for ukrypterte brukere (kan tas som egen forbedring
  senere; holdes utenfor for å begrense endringsflaten).
