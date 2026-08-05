# Raskere kvittering + eksport av merkede lenker

Dato: 2026-08-06. Bygger på `2026-07-26-my-links-v3-design.md` (samme
datamodell, ingen skjemaendringer).

## Del 1: «✓ Sendt»-vinduet skal knapt synes

### Bakgrunn

Bookmarkleten åpner et lite vindu mot `GET /_/api/sendlink` — vinduet *er*
transporten, valgt fordi sidens CSP kan blokkere `fetch`/`sendBeacon`, men
ikke en vindusnavigasjon. Svarsiden (`sent_page_html`) viser «✓ Sent» og
lukker seg etter 900 ms.

Nøkkelinnsikt: nedtellingen starter først når serveren har svart — altså
*etter* at lenken er lagret/sendt. Å korte ned eller fjerne ventetiden kan
ikke miste lenker. Den synlige ventetiden før svaret (blank popup mens
Anvil-serveren jobber) er ofte lengre enn selve kvitteringen.

### Endringer

1. **Kvitteringstiden ned fra 900 til 300 ms** i `sent_page_html`
   (`server_code/logic.py`). Serverside — når alle brukere umiddelbart,
   også de som dro bookmarkleten sin for lenge siden.
2. **Popupen viser «Sending...» med en gang** i stedet for å stå blank til
   serveren svarer: bookmarkleten åpner vinduet tomt, skriver placeholder
   med `document.write`, og navigerer det så til endepunktet.
   `document.write` pakkes i `try/catch`: gjenbrukes et gammelt
   send2me-vindu (samme vindusnavn) står det på et annet origin, og da
   kaster skrivingen — navigasjonen skal skje uansett.
   Bookmarklet-endringen når bare nye registreringer og brukere som drar
   lenken på nytt fra Settings; fallbacken `location.href=u` (blokkert
   popup) er uendret.

### Ikke valgt

- Lukke vinduet umiddelbart (0 ms): sparer 300 ms, men brukeren mister
  bekreftelsen. Feilsider lukker seg uansett aldri selv.
- Toast på selve siden + poll på `w.closed`: mest polert, men mest
  bookmarklet-kode for en endring eksisterende brukere aldri ser.

## Del 2: Eksporter bare merkede lenker

### Mål

Kunne merke enkeltlenker og eksportere kun dem — og kunne «merk alle» etter
et filter, gjentatte ganger med ulike filtre, slik at utvalget samles opp
på tvers av filtre før eksporten.

### Utvalgsmodellen

- `selected_ids`: et sett med lenke-id-er i `LinksForm`. Kun i nettleseren,
  ingenting lagres på serveren. Utvalget overlever filter-, sorterings- og
  sidebytter (det er poenget), og ryddes når lenker slettes.
- **Avkryssing per rad:** liten, grå checkbox som ny første kolonne i
  `LinkRow`. (Klikk-på-rad forkastet: for lett å treffe ved inline-
  redigering av tags/notat. Stjerner forkastet: de betyr noe annet.)
- **Merk alle (gjentakbart):** checkbox i kolonneoverskriften som virker på
  *hele* det filtrerte settet (ikke bare de 100 tegnede radene — samme
  filosofi som søket). Klikk når ikke alt er merket → legg alle treff til
  utvalget. Klikk når alle treff alt er merket → fjern *akkurat dem*,
  behold resten. Slik akkumulerer man: filter A → merk alle → filter B →
  merk alle → eksporter unionen.
- **Synlighet og nullstilling:** pille i verktøylinja, «23 selected ✕»,
  synlig når utvalget er ikke-tomt; klikk tømmer alt.
- **Eksport:** samme ⬇-ikon. Med utvalg eksporteres bare de merkede
  (tooltip sier antallet); uten utvalg eksporteres alt som før. Ingen ny
  knapp.

### Serverside

`export_csv(token, ids=None)` i `server_code/api.py`: `ids=None`/tom →
alle (dagens oppførsel). Ellers filtreres brukerens egne rader mot
id-settet (eierskap er alt avgrenset av e-postsøket). Filtreringen ligger
som ren funksjon `logic.links_by_ids`. CSV bygges fortsatt på serveren —
Anvil-klientens Python (Skulpt) mangler `csv`-modulen.

### Ren logikk (testes lokalt)

I `client_code/links_view.py`:

- `toggle_select_all(selected_ids, matched_ids)` — semantikken over.
- `all_selected(selected_ids, matched_ids)` — styrer header-checkboxens
  tilstand etter hvert filterbytte; False for tomt treff.
- `prune_selection(selected_ids, links)` — kast id-er som ikke finnes
  lenger.
- `selection_label(n)` — «3 selected», tom streng for 0.

I `server_code/logic.py`: `links_by_ids(links, ids)`.

### Layout

Gridet i `theme.css` som deles av overskriftsraden og radene får en ny
første kolonne (~18 px). Merk: mobilvisningen plasserer cellene med
`nth-child` — alle indekser forskyves med én. Mobil: checkboxen inn i
første linje, foran stjernene; dato rykker inn under stjernene.

### Testing

Nye enhetstester for de rene funksjonene (begge testfiler), inkludert
akkumulering på tvers av filtre og at «fjern» bare tar treffene. UI-lim
(forms, yaml, css) testes ikke lokalt — som ellers i repoet — og må
etterses i kjørende app etter deploy.
