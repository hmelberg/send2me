# My links v3 — rolig oversikt, én lenke per rad

Dato: 2026-07-26. Erstatter arkiv-UI-et fra
`2026-07-25-send2me-v2-mylinks-design.md` (samme datamodell, ny presentasjon
og 0–3 stjerner i stedet for av/på).

## Problemet

Dagens side viser innstillinger (modus, current tag, Save settings) og
handlinger (Export CSV, Delete everything) rett under overskriften, før
lenkene. Innstillinger settes én gang; lenkelista leses hver dag. Rekkefølgen
er altså snudd. Hver lenke flyter dessuten over flere linjer fordi rada er en
FlowPanel som brekker, og kortet er begrenset til 56 rem selv på brede skjermer.

## Hva v3 endrer

1. **Innstillinger bak et tannhjul.** Overskriftsrada får en høyremeny:
   current tag som en liten pille, et nedlastingsikon for Export CSV, og
   tannhjulet. De to tingene man gjør ofte — bytte stikkord og hente ut CSV —
   ligger dermed ett klikk unna, mens panelet bak tannhjulet (e-post,
   sendemodus, Delete everything) er skjult som standard.
2. **Én lenke = én rad.** Seks kolonner i CSS-grid: stjerner, dato, tittel,
   stikkord, notat, slett. Stikkord og notat redigeres inline på rada.
3. **0–3 stjerner** i stedet for boolsk stjerne.
4. **Verktøylinje** over lista: fritekstsøk (tittel, URL, stikkord, notat),
   stikkord-nedtrekk, dato-nedtrekk, «Clear». Den er høyrestilt, i flukt med
   ikonene i overskrifta, og bevisst nedtonet — 13 px i Gray 600 mot lenkenes
   15 px, med lyse rammer og blek nedtrekkspil. Hver kontroll skjerpes til
   svart tekst og blå ramme når den får fokus, så den er tydelig i bruk og
   stille ellers. Filteret er et verktøy man tar fram, ikke noe som skal
   konkurrere med lista.
5. **Sortering via kolonneoverskrifter** (★, Date, Title) — klikk snur retning.
6. **Bredere kort** som bruker skjermens bredde (inntil 1500 px).

## Layout

```
┌────────────────────────────────────────────────────────────────────┐
│  My links                     24 links   🏷 [helse    ]   ⬇    ⚙   │
│               [ Search title, tags, notes… ] [Tag ▾] [Any time ▾] Clear │
│                                                                    │
│   ★     Date        Title                 Tags        Note         │
│  ★★☆   07-24   Helseatlas 2026 ↗          helse       les kap 3  ✕ │
│  ★☆☆   07-23   SSB tabell 07459 ↗         data, ssb              ✕ │
│  ☆☆☆   07-21   Lancet: obesity trends ↗   helse       til møtet  ✕ │
└────────────────────────────────────────────────────────────────────┘
```

Tannhjulet folder ut over lista:

```
│  My links                     24 links   🏷 [helse    ]   ⬇    ⚙   │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Signed in as hans.melberg@gmail.com                          │  │
│  │ When I click the bookmark: [Email and save ▾]  [Delete all]  │  │
│  └──────────────────────────────────────────────────────────────┘  │
```

Under 480 px legger overskrifta seg på to linjer: tittelen øverst, så
antall, tag-pilla og ikonene.

Datoen vises som `MM-DD` for inneværende år og `YYYY-MM-DD` ellers, slik at
kolonna holder seg smal uten å bli tvetydig.

`✕` vises bare når musepekeren er over rada. Det gjør sletting tilgjengelig
uten bekreftelsesdialog og uten at lista ser ut som et kontrollpanel.
«Delete everything» beholder `confirm()`.

## Stjerner

Tre klikkbare glyffer per rad. Klikk på stjerne *n* setter verdien til *n*;
klikk på stjerna som allerede er høyest satt nullstiller. Verdien lagres med
det samme (`update_link`), uten at lista sorteres på nytt — rader skal ikke
hoppe under fingeren.

Databasen får en ny kolonne `stars` (number). Den gamle `starred` (bool)
beholdes og holdes i synk (`starred = stars > 0`), av to grunner: rader som
ble stjernemerket før v3 har `stars = None`, og da leses `starred` som
fallback (1 stjerne); og eksisterende `?starred=1`-kall mot API-et fortsetter
å virke. Første `update_link` på en rad skriver begge kolonnene, så
fallbacken gjelder bare rader ingen har rørt.

## Filtrering og sortering — hvor logikken bor

Alle lenkene lastes én gang ved åpning. Filtrering og sortering skjer i
klienten, så søk oppdaterer lista uten tur-retur til serveren.

Den rene logikken legges i **`client_code/links_view.py`** — et klientmodul
uten anvil-avhengigheter, med bare strengsammenlikninger og `datetime` for
dato-avkortingen. Da kan den enhetstestes lokalt på samme måte som
`server_code/logic.py`, i stedet for å være begravd i en skjemaklasse.

Datoene som kommer fra serveren er allerede strenger på formen
`YYYY-MM-DD HH:MM`, så filtrering er ren prefiksammenlikning:
`link["saved"][:10] >= cutoff`.

Modulens grensesnitt:

| Funksjon | Gjør |
|---|---|
| `stars_of(link)` | 0–3, med `starred`-fallback |
| `day_of(link)` | `YYYY-MM-DD` fra `saved` |
| `cutoff(preset, today)` | `"7"`/`"today"`/`""` → `YYYY-MM-DD` eller `None` |
| `all_tags(links)` | sorterte, unike stikkord til nedtrekket |
| `filter_links(links, search, tag, since)` | filtrert liste |
| `sort_links(links, key, descending)` | `key` ∈ `saved`/`stars`/`title` |
| `format_day(day, this_year)` | `MM-DD` eller `YYYY-MM-DD` |

Datovalgene er ferdige intervaller (Any time, Today, Last 7 days, Last 30
days, Last 3 months, Last 12 months) framfor to datovelgere. Det dekker det
man faktisk spør om («hva lagret jeg denne uka?») på én kontroll i stedet for
to, og API-et har fortsatt `since`/`until` for presise uttrekk.

## Server

`server_code/logic.py`:
- `clamp_stars(n)` → 0–3, `link_stars(stars, starred)` for fallbacken.
- `parse_links_query` bytter `starred`-flagget mot `min_stars`
  (`?stars=2` = minst to; `?starred=1` beholdes som alias for `stars=1`).
- CSV-kolonna `starred` blir `stars` med verdi 0–3.

`server_code/api.py`:
- `_link_dict` tar med `stars`.
- `update_link(token, link_id, tags=, note=, stars=)` — `starred`-parameteren
  erstattes av `stars`, og begge kolonnene skrives.
- `sendlink` setter `stars=0` på nye rader.

## Komponentstruktur

`LinkRow` beholder FlowPanel som rot, men gutteren gjøres om til CSS-grid via
rolla `link-row`. Overskriftsrada bruker rolla `link-head` med *samme*
`grid-template-columns`, så kolonnene står i flukt. Under 760 px bryter grid-en
til tre rader per lenke og overskriftsrada skjules.

Rada varsler skjemaet om sletting og stikkordendring med Anvils
RepeatingPanel-mønster — `self.parent.raise_event('x-link-deleted', link=…)` —
slik at `LinksForm` kan fjerne lenka fra sin egen liste og oppdatere
stikkord-nedtrekket. Ingen av dem trenger å kjenne den andres innmat.

Nye roller i `theme/parameters.yaml`: `page-header`, `header-count`,
`header-icon`, `header-tag`, `header-tag-icon`, `header-tag-input`,
`status-line`, `settings-panel`, `settings-email`, `settings-label`,
`login-panel`, `toolbar`, `toolbar-search`, `toolbar-clear`, `link-head`,
`head-cell`, `link-list`, `link-row`, `stars`, `star`, `row-date`,
`row-title`, `row-input`, `row-delete`, `empty-state`.

## Innstillinger som lagrer seg selv

Med current tag flyttet til overskrifta ville en «Save settings»-knapp bety at
man måtte treffe to steder for å bytte stikkord. Begge innstillingene lagrer
seg derfor selv — taggen når feltet forlates eller man trykker Enter, modus
når nedtrekket endres — og knappen er fjernet. `_save_settings` sammenlikner
mot sist lagrede verdi og hopper over kallet når ingenting er endret, så det
koster ingenting å klikke ut av tag-feltet. `save_settings` returnerer den
normaliserte taggen, som skrives tilbake i feltet og bekreftes på statuslinja
(«Saving new links as: helse»).

## Testing

- `tests/test_links_view.py` (ny): filtrering, sortering, stjerne-fallback,
  dato-avkorting, stikkord-samling, datoformat.
- `tests/test_logic.py`: `starred`-testene skrives om til `min_stars`, ny test
  for `clamp_stars`/`link_stars`, CSV-headeren oppdateres.
- Kjøres med `python3 -m unittest discover -s tests -v` fra repo-rota.

## Anvil-CSS-feller funnet under arbeidet

Verifisert mot den kjørende appen, ikke bare mot en mock:

- **Anvil skriver `justify-content` som INLINE-stil på `.flow-panel-gutter`**,
  ut fra FlowPanelens `align`-egenskap (default `left` → `flex-start`). En
  vanlig regel i temaet blir stilltiende ignorert. Verktøylinja er derfor satt
  til `align: right` *og* har `justify-content: flex-end !important` i CSS-en.
  Målt live: uten den endte siste element på 427 px, med den på 1416 px = kortkanten.
- **`.content > * > .anvil-container {padding: 16px 24px}`** (0,2,0) slår en
  ren rolle-selektor (0,1,0). Kortets egen padding må derfor skrives
  `.anvil-container.anvil-role-wide-card` for å vinne.
- FlowPanel-DOM-en er `.flow-panel > .flow-panel-gutter > .flow-panel-item`,
  der hvert item har inline `width: auto` og klassen
  `anvil-always-inline-container`. LinearPanel rendres som `<ul><li>`.
- Temaet animerer `border-bottom` i 0,2 s; måler man rett etter `.focus()`
  leser man overgangsverdien, ikke sluttverdien.

## Utrulling

Skjemaendringen (`stars`-kolonna) gjør at Anvil-editoren må åpnes og pull
godtas med **«source code»**-skjemaet, ikke «default database schema» — samme
felle som ved v2. Forsiden kan ikke verifiseres med ren HTTP-fetch; verifiser
mot `GET /_/api/links?token=…` i stedet.
