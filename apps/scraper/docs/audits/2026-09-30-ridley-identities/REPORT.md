# TASK-4082: Ridley conflicting performance identities

## Authoritative source resolution

The September 30 live venue calendar still groups five Etix performance IDs under conflicting series titles. Its existing parser returns 99 unambiguous events and excludes those five. Six official series pages repeat the conflicting associations, so neither series labels nor ticket URL slugs can establish the correct title.

Each ticket button also references a WordPress post ID through its `ctaspan-` identifier. Following the official same-origin `/?p=<post ID>` URL retrieves an individual event page. All five individual pages provide one Event JSON-LD object containing the exact Etix performance ID, dated local start with UTC offset, canonical event URL, title and venue. The main visible heading and showtime corroborate that record; nested series lists do not override it.

| Etix ID | WordPress post | Verified title | Venue-local start |
| --- | --- | --- | --- |
| 62115951 | 34020 | MIKE CRONIN | 2026-10-15 19:30 EDT |
| 84649375 | 34022 | MIKE CRONIN | 2026-10-16 19:15 EDT |
| 68862675 | 27696 | COMEDY RUMBLE | 2026-10-30 19:15 EDT |
| 82720075 | 27698 | COMEDY RUMBLE | 2026-10-30 21:45 EDT |
| 50537895 | 21912 | THE NIGHT BEFORE THANKSGIVING COMEDY SPECIAL | 2026-11-25 19:30 EST |

All five name Mark Ridley's Comedy Castle, Royal Oak. The official pages give 310 South Troy Street. The existing database address is 269 E. Fourth Street; this task does not infer an address correction from that difference. Venue identity must remain tied to the configured official host, exact normalized venue name, and city, rather than silently equating different street addresses.

Etix direct ticket pages returned DataDome challenges through the scraper HTTP stack and browser fallback. Those responses are not event evidence. Individual venue pages independently establish the identities. Their JSON-LD price zero is a placeholder and is not evidence of free admission.

The five reviewed records, canonical source links, ticket URLs, and timezone offsets are in verified-performances.json. Fetch URLs and content hashes are in source-fetch-summary.json. Raw HTML is excluded from Git.

## Reproduction and baseline

Single-club scheduled-environment run [36798084830](https://github.com/gioe/laughtrack/actions/runs/36798084830) completed using the current main branch. It retained 99 events, recorded fetches_ok=1 and fetches_failed=1, explicitly listed all five conflicts, and blocked stale reconciliation. The run's metrics and subsequent future database inventory are saved alongside this report. The database contains exactly those 99 source ticket IDs, with no extra or missing safe IDs. This confirms the missing performances are a current source-mapping problem despite a successful job status. No stale future row is slated for retirement.

## Implementation and post-change verification

The resolver now follows the unambiguous calendar CTA post ID to a same-origin individual event record. It requires exact performance identity, visible/structured title and time agreement, the club timezone, venue name, and matching independently published calendar/detail address. At most eight posts are requested, with two concurrent requests and an eight-second per-request timeout. Unresolved conflicts retain the existing diagnostics and block stale reconciliation. Placeholder JSON-LD prices are ignored.

The focused Etix suite passed 121 tests, including card-order invariance, mismatched identity/time/offset/venue/address/title, missing or competing post IDs, and partial-resolution cleanup guards. The actual live read-only scraper returned 104 performances and correctly resolved all five reviewed records; readonly-preview.json contains the output. Scheduled-environment run [36802399000](https://github.com/gioe/laughtrack/actions/runs/36802399000), using commit 06fc4b8a0356d3f4836319ef4effcf3a3de74e9f, saved 104 performances: five inserts and 99 updates, with zero failed fetches, validation failures, save failures or database errors. The log confirms all five conflicts were verified from individual posts; no unresolved-conflict cleanup guard remained. Post-run production queries verified each restored ticket identity exactly once with its authoritative title and time. All 105 pre-existing show IDs and their name, date, room and page URL were preserved; the total inventory increased to 110. See scheduled-verification-metrics.json and production-verification.json. The full scraper commit test gate also passed.
