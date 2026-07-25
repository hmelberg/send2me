# send2me v2 — «My links» designspec

*Dato: 2026-07-25. Status: godkjent muntlig («kjør»). Bygger på v1-spec
(2026-07-24); alt der gjelder fortsatt med mindre det overstyres her.*

## Mål

Lenker kan **lagres i appen** i tillegg til (eller i stedet for) e-post, styrt av
en innstilling per bruker. Brukeren får en egen arkivside («My links») med
visning, redigering, sletting og eksport — pluss et API for programmatisk
uthenting med kø-semantikk.

## Identitet: nøkkelen er kontoen

Ingen Users-tjeneste. Den personlige nøkkelen (fra registrerings-eposten) er
også innloggingen til arkivsiden. Adgangslenken er en **vanlig URL** med
nøkkelen i hash-delen:

    https://send2me.app/#?key=<TOKEN>

- Hash sendes aldri til serveren → havner ikke i logger.
- Vanlig URL → klikkbar i e-posten (strippes ikke som `javascript:`), kan
  bokmerkes/dras til verktøylinjen, og får ekte favicon (papirflyet).
- Kan også limes inn manuelt på arkivsiden.

Oppstartsformen ruter: `#?key=` til stede → LinksForm, ellers RegisterForm.
Steg 2 på registreringssiden genererer nå **to** elementer: ✈️ send2me
(bookmarklet, uendret) og 🔑 my links (vanlig lenke). Begge står i e-posten.

## Sendemodus per bruker

`subscribers` får kolonnen `mode`: `email` | `save` | `both`. Manglende/ukjent
verdi behandles som `both` (default). Settes på arkivsiden. `/sendlink` gjør
e-post, lagring eller begge — bookmarkleten og URL-formatet er **uendret**.
Kvitteringssiden viser «Saved» når modus er kun lagring, ellers «Sent».

## Stikkord, notater, stjerner

- **Klebrig stikkord:** `subscribers.current_tag` (fritekst, gjerne
  kommaseparert). Alt som lagres merkes automatisk med gjeldende verdi til den
  endres/tømmes. Settes på arkivsiden; synlig der. Lagringsklikket spør ALDRI
  om noe — det prinsippet er hellig.
- **Per lenke:** `tags` (fritekst), `note` (fritekst), `starred` (bool) —
  redigerbare inline på arkivsiden (lagres ved lost_focus / stjerneklikk).
- Bevisst forkastet: bookmarklet som spør om stikkord ved lagring (bryter
  ett-klikks-prinsippet); egne tag-tabeller (YAGNI — fritekst holder for
  personlig skala).

## Datamodell

Ny tabell `links`: `email` (string), `url` (string), `title` (string),
`saved` (datetime), `fetched_at` (datetime, None = uhentet), `tags` (string),
`note` (string), `starred` (bool).
`subscribers` +: `mode` (string), `current_tag` (string).

## Arkivsiden (LinksForm)

- Uten nøkkel: felt for å lime inn nøkkel + «Open my links».
- Med nøkkel: e-postadressen vises; innstillinger (modus-dropdown + klebrig
  stikkord + Save); liste nyest først via RepeatingPanel med radmal LinkRow:
  dato, ★-toggle, tittel som lenke (åpner artikkelen; tilbakeknappen tar deg
  til arkivet igjen siden nøkkelen ligger i URL-hashen), stikkord- og
  notatfelt (autolagres ved lost_focus), ✕ sletter raden.
- «Export CSV» (server bygger CSV → nedlasting) og «Delete everything»
  (med bekreftelse) — viktig hygiene når vi lagrer folks nettleservaner.

## API for uthenting

`GET /_/api/links?token=...` → JSON `{ok, count, links: [...]}`.
Kwargs: default kun **uhentede**, som merkes hentet (kø-semantikk);
`all=1` (alt), `keep=1` (ikke merk), `since=ÅÅÅÅ-MM-DD`/`until=` (datoer),
`tag=` (case-ufølsomt treff i tags-listen), `starred=1`. Ugyldig dato →
`{ok: false}`. Samme logikk eksponeres som server-callable `get_links` for
Uplink-bruk (kun Hans — Uplink-nøkkelen er app-vid og deles ikke).

## Testbarhet

All filter-, validerings- og CSV-logikk i `logic.py` (ren stdlib, unittest):
modus- og stikkordnormalisering, query-parsing, radmatching, CSV-bygging,
URL-/e-posttekstbygging. Anvil-limet forblir tynt.

## Kjente kostnader/begrensninger

- Skjemaendring → Hans må godta «source code» i Anvil-editoren ved neste pull.
- E-postkvoten (gratisnivå) er fortsatt flaskehalsen ved modus `both`/`email`.
- Token i query for `/links`-endepunktet havner i serverlogger — samme
  aksepterte trusselmodell som `/sendlink`.
