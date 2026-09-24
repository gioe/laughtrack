# Same-city venue assignment audit — TASK-4049

Evidence refreshed September 24, 2026. The initial production query found 33 event-specific URLs assigned to two same-city clubs (66 rows). Primary-source review expanded the confirmed duplicate set to 58 stale rows: 24 additional Eventbrite URL-slug variants and one separately verified John Mulaney performance.

## Dispositions

| Pair | Decision | Confirmed stale show rows | Identity treatment |
| --- | --- | ---: | --- |
| Attic 575 / Walrus 29044 | Temporary relocation to Walrus | 41 | Keep both venues and their sources |
| Van Wezel 10023 / 12796 | Duplicate theater records | 12 | Canonical 12796; retain hidden closed 10023 |
| Mahalia Jackson 5225 / 5364 | Duplicate theater records | 2 | Canonical 5364; retain hidden closed 5225 |
| State Theatre Ithaca 5115 / 5114 | Duplicate theater records | 1 | Canonical 5114; retain hidden closed 5115 |
| Yaamava resort 4691 / Theater 9650 | Separate identities within one complex | 2 | Keep both; these performances belong to Theater 9650 |

The [Attic homepage](https://theatticcomedyclub.com/) and [performer listings](https://theatticcomedyclub.com/comedians) announce temporary relocation after water damage at Oak Street. All 41 live Eventbrite records identify venue 298963768, The Walrus, 143 E Main Street. Every match has the same provider event ID and UTC start; 24 differ only in URL slug. The existing organizer scraper routes events using their current physical venue, so the Attic organizer source remains enabled for eventual return.

[Van Wezel](https://www.vanwezel.org/) identifies 777 N Tamiami Trail. Queries for its two Discovery venue IDs returned the same 52 event IDs. Eleven duplicate performances share exact URLs. The remaining [John Mulaney performance](https://www.vanwezel.org/events/detail/john-mulaney-mister-whatever) is an explicit reviewed exception: different Discovery event IDs, but one official December 10, 7:30 p.m. show, tickets.com event 4504, and matching UTC start and theater. This is not a general same-title merge rule.

[Mahalia Jackson venue information](https://us.atgtickets.com/venues/mahalia-jackson-theater/venue-info/) establishes 1419 Basin Street. Both Discovery venue IDs return the same nine event IDs. [State Theatre Ithaca](https://stateofithaca.org/about/) gives 107 West State Street; its two Discovery venue queries return the same four event IDs. These address/name variants represent duplicate records for their respective theaters.

[Yaamava entertainment](https://www.yaamava.com/entertainment) includes multiple spaces. Its resort and theater accounts have different event inventories. The exact Ron White and Nikki Glaser events embed Theater venue ID Z7r9jZaAVT. Only those two assignments are repaired; no resort-wide alias or source remapping is justified.

## Unresolved cohort

Sixteen Attic rows covering eleven Eventbrite IDs lack current confirmation: the API returns HTTP 403. This does not establish cancellation, relocation, or a changed start time. They remain unchanged and are tracked in **TASK-4079**. Exact IDs, dates and URLs are in `source-evidence.json` under `attic_unresolved`.

## Repair and recovery policy

The dated one-shot script merges only enumerated, source-reviewed future show IDs. For the three true duplicate venues, it retains the old club records as hidden/closed, creates verified aliases, moves their source-ID mappings onto the canonical club in a disabled state, and preserves the enabled canonical source. Stable provider-ID lookup takes precedence over aliases, making source remapping necessary to prevent re-creation.

Historical shows, scrape history and historical click attribution remain on retained original club records. Future show references are consolidated onto their enumerated survivors. The script inventories incoming foreign keys and rejects unexpected relationship or identity changes before writing. Full before/after records are stored in a private recovery file, never in this audit directory. Restoration checks exact post-repair state and restores original primary keys and values; it refuses intervening changes.

`source-evidence.json` contains public source facts and identifiers, with long descriptions and unrelated response fields omitted. It contains no private user-reference snapshot.

## Execution and verification

Pending guarded PostgreSQL fixture tests, production dry-run, application, and subsequent source-routing verification. Final results will be recorded before task completion.
