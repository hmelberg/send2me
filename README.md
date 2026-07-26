# send2me

Send lenken til siden du leser til din egen e-post — ett klikk, ingen skriving.
Live på **https://send2me.app/**

## Slik virker det

1. Registrer e-postadressen din på send2me.app → du får en personlig nøkkel på e-post.
   (Nøkkelen vises aldri på skjermen: den som har nøkkelen, har bevist at de eier
   innboksen — og nøkkelen kan bare sende lenker til sin egen eier.)
2. Lim inn nøkkelen på siden og dra den genererte «send2me»-lenken til bokmerkelinjen.
3. Stå på en hvilken som helst side og klikk på bokmerket: den fullstendige URL-en
   sendes til deg. Et lite «✓ Sendt»-vindu lukker seg selv etter ett sekund.

Bookmarkleten åpner et vindu mot `GET /_/api/sendlink` i stedet for å bruke
`fetch` — dermed stopper ikke nettsiders CSP den, og URL-en sendes eksplisitt
som parameter (Referer-headeren inneholder bare domenet i moderne nettlesere,
som var feilen i forrige versjon av denne appen).

## My links (v2)

Nøkkelen er også innloggingen: e-posten inneholder en personlig arkivlenke
`https://send2me.app/#?key=<NØKKEL>` (nøkkelen ligger i hash-delen og sendes
aldri til serveren). Dra den til bokmerkelinjen som «🔑 my links», eller lim
inn nøkkelen manuelt på siden.

Lenkelista er det eneste som står i fokus. Én lenke = én rad, med stjerner,
dato, tittel, stikkord og notat i faste kolonner:

- **Høyremeny i overskrifta:** current tag som en pille (🏷), Export CSV som
  nedlastingsikon (⬇) og tannhjulet (⚙). Tannhjulet åpner en modal med e-post,
  sendemodus, bookmarklet-lenkene og «Delete all my links» (egen linje, ikon,
  bekreftelse).
- **Sendemodus per bruker:** *Email me the link* / *Save to My links* /
  *Email and save* (default). Bookmarkleten er uendret uansett modus.
- **Klebrig stikkord:** skriv i tag-pilla i overskrifta — alt som lagres
  merkes automatisk til taggen endres/tømmes. Lagringsklikket spør aldri om noe.
- **Ingen «Save settings»-knapp:** både taggen og modusen lagrer seg selv
  (taggen når feltet forlates eller ved Enter, modusen når den endres).
- **Ny maskin?** Bookmarklet-lenkene kan dras på nytt fra innstillings-modalen
  — man trenger ikke lete opp registrerings-eposten.
- **Mobil:** to linjer per lenke, og notatet er foldet bort bak et ikon som
  lyser når det finnes et notat.
- **Grenser:** maks 1000 lenker per bruker (eldste ryker først, stjernemerkede
  spares), og e-posten sier fra om at tjenesten ikke gir garantier.
- **Per lenke:** 0–3 stjerner (klikk stjerne *n* for den verdien, klikk den
  øverste igjen for å nullstille), stikkord og notat redigeres inline og
  autolagres. ✕ til høyre sletter (vises når musa er over rada).
- **Filtrering:** fritekstsøk i tittel, URL, stikkord og notat i verktøylinja,
  og stikkordfilter som nedtrekk i TAGS-kolonneoverskriften. ✕ nullstiller.
- **Sortering:** klikk kolonneoverskriftene ★, Date eller Title; klikk igjen
  for å snu retningen.
- **Lange lister:** 100 lenker vises om gangen, med «Showing 100 of 342 —
  Show more» nederst. Bunnlinja er skjult når alt får plass. Filtrering og
  sortering skjer over hele settet før kuttet, så søket når også lenker som
  ikke er tegnet opp ennå.

Filtrering og sortering skjer i nettleseren over lenkene som alt er lastet, så
søket oppdaterer lista uten tur-retur til serveren. Den rene logikken ligger i
`client_code/links_view.py` og testes lokalt som resten.

### API

```
curl "https://send2me.app/_/api/links?token=NØKKEL"            # uhentede; merkes hentet
curl "https://send2me.app/_/api/links?token=NØKKEL&all=1"      # alt
curl "https://send2me.app/_/api/links?token=NØKKEL&keep=1"     # ikke merk som hentet
curl "https://send2me.app/_/api/links?token=NØKKEL&since=2026-07-01&until=2026-07-31"
curl "https://send2me.app/_/api/links?token=NØKKEL&tag=helse&stars=2"   # minst to stjerner
```

Svar: `{"ok": true, "count": n, "links": [{url, title, saved, fetched_at,
tags, note, stars}, ...]}` der `stars` er 0–3. `?starred=1` er beholdt som
alias for `?stars=1`. Samme funksjon er server-callable for Uplink:
`anvil.server.call('get_links', NØKKEL, all=1)`.

## Utvikling

- Repoet er git-synket med Anvil-appen: push til `master` → Anvil henter og
  deployer automatisk.
- Ren logikk ligger i `server_code/logic.py` og `client_code/links_view.py`
  (kun stdlib) og testes lokalt: `python3 -m unittest discover -s tests -v`
- Anvil-lim (server-callables + HTTP-endepunkt) i `server_code/api.py`,
  UI i `client_code/RegisterForm/`, `LinksForm/`, `LinkRow/` og `SettingsForm/`.
- Etter en skjemaendring (som `stars`-kolonna) må Anvil-editoren åpnes og
  pullen godtas med **«source code»**-skjemaet, ikke «default database schema».
- Rate-grense: maks 3 registrerings-eposter per adresse per dag.
  Merk: Anvils gratisnivå har begrenset e-postkvote.

Design-spec og plan: `docs/superpowers/`.
