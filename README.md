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

## Utvikling

- Repoet er git-synket med Anvil-appen: push til `master` → Anvil henter og
  deployer automatisk.
- Ren logikk ligger i `server_code/logic.py` (kun stdlib) og testes lokalt:
  `python3 -m unittest discover -s tests -v`
- Anvil-lim (server-callables + HTTP-endepunkt) i `server_code/api.py`,
  UI i `client_code/RegisterForm/`.
- Rate-grense: maks 3 registrerings-eposter per adresse per dag.
  Merk: Anvils gratisnivå har begrenset e-postkvote.

Design-spec og plan: `docs/superpowers/`.
