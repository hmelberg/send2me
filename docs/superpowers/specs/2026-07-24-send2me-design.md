# send2me — designspec

*Dato: 2026-07-24. Status: revidert til bookmarklet-alene; venter på endelig gjennomlesing.*

## Mål

Én bokmerke-lenke («send2me» på bokmerkelinjen) som med **ett klikk, uten
bekreftelse**, sender den **fullstendige URL-en** til siden du står på (ikke bare
root-domenet) til din egen e-postadresse. Fungerer på desktop, mobil og låste
jobbmaskiner — ingen installasjon. Backend og registreringsside er Anvil-appen
som allerede ligger på **https://send2me.app/** (gammel, feilende kode der
erstattes i sin helhet).

**Bevisst valg: ingen nettleserutvidelse i v1.** Ett produkt, én forklaring:
«gå til send2me.app, registrer deg, dra lenken til bokmerkelinjen». En utvidelse
med diskret badge-feedback kan legges til senere hvis popup-blinket (se under)
irriterer i daglig bruk.

## Kjerneidé for sikkerhet: token-i-innboksen

Registrering skjer ved at serveren genererer en personlig token og **sender den på
e-post** til adressen som registreres. Tokenen vises aldri på skjermen. Den som har
tokenen har dermed bevist at de eier innboksen — og tokenen kan bare brukes til å
sende lenker **til den adressen den er koblet til**. Misbruk mot tredjepart er
derfor begrenset til å utløse registrerings-eposter, som rate-begrenses
(maks 3 per adresse per dag).

## Struktur

Anvils **innebygde GitHub-synk** eier koblingen (satt opp 2026-07-24): appen
send2me på anvil.works ↔ GitHub-repoet `hmelberg/send2me`, toveis. Vi jobber
mot GitHub-repoet; Anvil henter endringer automatisk. Appen ligger i repo-roten
(Anvil ignorerer ekstra filer som docs/):

```
send2me/                     # = Anvil-appens repo, synket av Anvil
  anvil.yaml                 # Email-tjeneste, Data Tables, tabellskjema, startup-form
  client_code/RegisterForm/  # registreringsside + bookmarklet-generator (norsk tekst)
  server_code/api.py         # registrering + /sendlink-endepunkt
  theme/                     # beholdes fra gammel app (inkl. papirfly-logo)
  README.md
  docs/superpowers/specs/    # denne spec-en
```

Det gamle spec-repoet er omdøpt til `send2me-old` på GitHub og kan slettes når
alt er flyttet hit.

## Funn fra den gamle appen (arkeologi, 2026-07-24)

Den gamle koden bekreftet begge designvalgene:

- **Root-URL-mysteriet er løst:** Gamle bookmarklet gjorde `fetch` til
  `/send/:email`, og serveren leste URL-en fra `Referer`-headeren. Moderne
  nettlesere sender som standard bare *origin* i Referer ved kryssdomene-kall
  (`strict-origin-when-cross-origin`) — derfor ble det alltid `https://www.vg.no/`
  og aldri artikkel-URL-en. Ny design sender URL-en eksplisitt som query-parameter
  og er immun.
- **`fetch` fra sidekontekst** var også CSP-utsatt (jf. bookmarklet-seksjonen) —
  ny design navigerer i stedet.
- **Ingen autentisering:** gamle endepunkt lot hvem som helst sende til hvilken
  som helst adresse — token-modellen tetter dette.
- **Gjenbrukes:** Email-tjenesten (aktivert og fungerende), temaet og
  papirfly-logoen, custom-domenet send2me.app (konfigurert utenfor git).
- **Ryddes/tilpasses:** Users-tjenesten (påloggingsopplegg) brukes ikke i ny
  modell og fjernes fra `anvil.yaml`; den gamle `users`-tabellen beholdes
  inntil videre i skjemaet for å unngå skjemakonflikt ved synk (kan slettes
  manuelt i Anvil senere). Serveren kjører `python3-sandbox` (gratisnivå) —
  tokengenerering med `secrets.token_urlsafe`, fallback `uuid4` hvis sandboxen
  skulle nekte.

## Bookmarkleten

- **Mekanisme:** Bookmarkleten kan *ikke* bruke `fetch` — den kjører i sidens
  kontekst, og mange nettsteder har CSP som blokkerer kall til fremmede domener.
  I stedet åpner den et lite vindu (plassert nede i hjørnet) mot `/sendlink` som
  **GET** med `?url=...&title=...&token=...`. Toppnivå-navigasjon blokkeres ikke
  av CSP. Vinduet viser «✓ Sendt» og lukker seg selv etter ~1 s. Hvis popup
  blokkeres (`window.open` returnerer null), fallback: naviger selve fanen dit,
  og svarsiden går tilbake med `history.back()`.
- **Mobil:** Samme bokmerke. iOS/Android åpner en fane som lukker seg selv
  (fallback-tekst «✓ Sendt — lukk fanen» hvis selvlukking nektes). Bokmerker
  synkes av nettleseren, så registrering én gang dekker alle enheter.
- **Generering:** Registreringssiden har en seksjon «Lag bokmerke-lenke»: lim inn
  tokenen fra e-posten → en ferdig, personlig lenke vises, klar til å dras til
  bokmerkelinjen. (E-posten kan ikke inneholde lenken direkte som klikkbar lenke —
  Gmail o.l. stripper `javascript:`-lenker.) Bookmarklet-strengen genereres
  **server-side** (`logic.bookmarklet_js`): den må uansett inn i
  registrerings-eposten som ren tekst for mobiloppskriften (lagre bokmerke,
  rediger, lim inn koden), og siden serveren allerede kjenner alle tokens,
  endrer ikke dette sikkerhetsmodellen. Siden kaller `make_bookmarklet` for å
  få nøyaktig samme streng.

## Anvil-appen

- **Én tabell** `subscribers`: `email` (string), `token` (string), `created`
  (datetime), `reg_date` (date) og `reg_count` (number) for rate-begrensning.
- **Registrering** via vanlig `anvil.server.call` fra RegisterForm (ikke
  HTTP-endepunkt): valider e-postformat, håndhev rate-grensen, generer token med
  `secrets.token_urlsafe`, lagre/oppdater raden (ny registrering gir ny token og
  ugyldiggjør den gamle), send e-post med token og bruksanvisning. Skjermen sier
  bare «sjekk innboksen din».
- **`/sendlink`** (HTTP-endepunkt, **GET**): slå opp token i tabellen; ukjent
  token → feilside; ellers send e-post til radens adresse med **emne =
  sidetittel** (fallback: URL) og **brødtekst = URL**. Svaret er en minimal
  HTML-side («✓ Sendt») som lukker vinduet / går tilbake. Merk: token i URL
  havner i serverlogger — akseptert i denne trusselmodellen (tokenen kan uansett
  bare sende til eieren).
- **RegisterForm:** tittel, kort forklaring, e-postfelt, «Registrer»-knapp,
  statuslinje, samt «Lag bokmerke-lenke»-seksjonen. Norsk tekst. (Draggbar
  `javascript:`-lenke kan kreve en rå HTML-komponent hvis Anvils Link-komponent
  sanerer URL-en — implementasjonsdetalj.)
- `anvil.yaml` deklarerer Email- og Data Tables-tjenestene og tabellskjemaet, slik
  at appen får alt ved git-push. Fallback dokumenteres i README: hvis
  skjemaimport skulle knirke, opprettes tabellen manuelt på 30 sekunder.

## Manuelle steg

1. ~~Sett opp GitHub-synk i Anvil~~ — **gjort 2026-07-24.** Implementasjonen
   pushes til GitHub og hentes av Anvil automatisk; den gamle app-koden
   erstattes (bevisst — den feiler i dag).
2. Etter bygging: verifiser at https://send2me.app/ viser registreringssiden
   (åpne appen i Anvil-editoren og sjekk at synken har hentet endringene hvis
   ikke).
3. Registrer deg, hent token fra innboksen, lim inn på siden, dra lenken til
   bokmerkelinjen.

## Bevisste begrensninger

- Popup-blinket ved sending er mindre diskret enn en utvidelses-badge —
  akseptert pris for null installasjon; utvidelse kan legges til senere.
- Enkelte ekstra herdede sider (og nettleser-interne sider) blokkerer
  `javascript:`-bokmerker helt.
- Ingen kø/retry ved nettverksfeil; ingen historikk; ingen avregistrering
  (raden slettes manuelt i Anvil ved behov). YAGNI.
- Anvils gratisnivå har begrenset e-postkvote — greit for personlig bruk; verdt å
  vite hvis mange registrerer seg.
