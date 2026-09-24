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

The guarded production dry-run passed and rolled back. The same plan then committed on September 24, 2026. A private 0600 recovery file was written and fsynced before commit at `~/.tusk/backups/laughtrack/task4049-recovery.json` (20,223,936 bytes). It contains user-reference rows and must stay private.

Production verification at 19:54 UTC found:

- **58 stale show rows removed**, all 58 enumerated survivors retained; cohort totals 381 → 323 shows.
- **Zero remaining cross-venue future URL clusters** among the ten audited clubs (previously 33).
- **Three verified aliases added**, all 15 source records retained, and duplicate source IDs routed onto their canonical venues while disabled.
- **All 7,332 click records preserved**, with merged future-show references repointed. All 963 scrape-run records and four historical notifications preserved.
- Ticket rows 381 → 323, lineup associations 218 → 166, and tag associations 1,585 → 1,368 after duplicate consolidation. Existing canonical ticket types and lineup roles win conflicts; superseded values remain recoverable in the private backup. No favorite-club or saved-show rows existed in this cohort; newly appearing unreviewed club relationships cause refusal.
- Every committed after-state row was still present with matching values. Historical show and attribution rows were retained. Sixteen unconfirmed Attic future rows remain for TASK-4079.

`production-verification.json` records sanitized counts and source disposition. `refresh-verification.json` records two repeated post-repair source replays: 41 Eventbrite events route to Walrus 29044 and both reviewed Yaamava events to Theater 9650, with exact source UTC starts. The helper uses real parsing, organizer routing and read-only production venue lookup; it substitutes captured API data and performs no show writes. It therefore proves repeatable routing, not a full live scheduler/persistence run.

Seventeen real PostgreSQL tests passed, covering 58 merges, exact restore, idempotence, reference preservation, schema/identity drift refusal, and repeated execution of the actual Ticketmaster venue UPSERT for both old and canonical IDs. Those refreshes retained the repaired canonical/source state. Together with captured current-source routing, these checks establish that the reviewed input reproduces canonical assignments. Future provider changes remain subject to normal monitoring.

The database-domain web gate had 2,408 passing tests and three unrelated failures in saved-show header tests. Three unchanged-HEAD precheck runs reproduced all three failures without flakiness or default-branch divergence. This existing expired-date fixture issue is **TASK-3983**; fresh evidence was attached there. The documented Tusk path-limited commit fallback was used.

Reproduce the targeted checks from `apps/scraper`:

```sh
TEST_DATABASE_URL=postgresql://localhost:55444/postgres PYTHONPATH=src:. .venv/bin/python -m pytest tests/scripts/core/test_repair_same_city_assignments.py -q
PYTHONPATH=src:. .venv/bin/python docs/audits/2026-09-24-same-city/verify_source_refresh.py
```

The first command requires a local PostgreSQL fixture database. The second uses the scraper environment for read-only production lookup and rewrites the replay result. Recovery is deliberately guarded: subsequent activity can make automatic restore refuse, requiring a reviewed reconciliation rather than overwriting new data.
