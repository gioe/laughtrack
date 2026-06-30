# TASK-3515 Empty Lineup Extraction Audit

Captured June 30, 2026 while triaging the June 29 scraping-data audit's
high-empty-lineup scrapers.

## Source Findings

| Scraper | Finding |
| --- | --- |
| `wix_events` | The Wix paginated-events API exposes title, description, scheduling, and registration/ticketing data. Live Bushwick Comedy Club sampling showed no structured performer/headliner field. Some titles do carry explicit headliner shapes such as `Matt Misci LIVE at ...`, `<name> @ ...`, `Comedy Legend <name> Returns`, or `<name> Comedy`. Those are now parsed into `Show.lineup`; generic Wix titles stay empty. |
| `vbo_tickets` | The VBO `showevents` listing exposes event title, category/subcategory, date text, room, price, and event URL. It does not expose a structured performer field. Exact two-word titles are deliberately not treated as people because VBO feeds include many music/group titles such as `Williamson Branch`. Explicit headliner-title shapes are eligible when present. |
| `denver_comedy_lounge` | `/shows` ItemList exposes title + detail URL only; detail Event JSON-LD is already used for offer price and did not provide a performer field in live sampling. Titles with explicit `Comedy Special` headliner shapes, e.g. `Garage Sale - Korey David Comedy Special`, are now parsed into lineup. Generic `Friday Night Comedy` / `Saturday Early Show` titles stay empty. |
| `tock` | Live BATSU! Chicago Tock Redux state produced recurring `JsonLdEvent` rows with name, description, location, offers, dates/times, and no performer/person field. Empty lineup is expected for this feed. |
| `anyroad` | Live Rozzie Square AnyRoad experiences produced name, description, price, location, image, URL, schedule/availability, and no performer field. Empty lineup is expected for this feed unless the title carries a future explicit headliner shape. |
| `esthers_follies` | Venue-specific VBO date-slider feed represents recurring Esther's Follies slots with date/time and seat tiers. The site presents the institution/show, not per-performance cast/headliners. Empty lineup is expected. |
| `east_austin_comedy` | Netlify availability API exposes dates/times for generic `Live Stand-Up Comedy` slots only. The source has no published lineup. Empty lineup is expected. |
| `stevie_rays` | Chanhassen ticket listing exposes generic `Stevie Ray's Comedy Cabaret` rows and date/time only. No per-performance cast/headliners are available. Empty lineup is expected. |
| `brasstix` | BrassTix inline calendar exposes production titles such as `DRUNK ROMEO & JULIET`, `DRUNK DRACULA`, and `A DRUNK CHRISTMAS CAROL`, with event ids, times, checkout URLs, availability, and prices. It does not expose performer/cast names. Empty lineup is expected. |

## Implementation Decision

Do not infer people from generic titles or exact title strings. The scraper
pipeline already has DB-backed known-comedian enrichment for existing comedian
names in show titles; this change only creates new lineup entries when the title
itself carries a narrow explicit headliner signal:

- `<name> LIVE at ...` / `<name> LIVE in ...`
- `<name> - Appearing ...`
- `<name> @ ...`
- `Comedy Legend <name> Returns ...`
- `<name> Comedy` / `<name> Comedy Special`
- `<production> - <name> Comedy Special`

Candidates are normalized through `ComedianUtils.normalize_name`, rejected if
they contain title/generic words, and passed through the shared
`detect_false_positive` guard before becoming lineup entries.

## Candidate Estimate

Running the tightened extractor over current upcoming empty-lineup rows matched
6 title groups / 10 show rows:

- Denver Comedy Lounge: `Garage Sale - Korey David Comedy Special` -> `Korey David` (5 rows)
- Clint's Comedy Club: `Comedy Legend David Naster Returns ...` -> `David Naster`
- Clint's Comedy Club: `Tim Bateman - Appearing ...` -> `Tim Bateman`
- Nick's Comedy Stop: `Matt Misci LIVE at Nicks 7/18` -> `Matt Misci`
- Shamrock Comedy Club: `Chris Renois @ Shamrock Comedy Club` -> `Chris Renois`
- The Leavitt Theatre: `Zach Zimmermann Comedy` -> `Zach Zimmermann`

The same pass explicitly rejected observed false positives including `RED ROOM
COMEDY`, `Playing with Matches Live Gameshow!`, `Jukebox Heroes LIVE!`, `The
Malpass Brothers LIVE`, and exact-name-looking production titles such as
`Williamson Branch`.
