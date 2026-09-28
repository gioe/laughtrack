# Event-specific organizer venue audit — September 28, 2026

TASK-4065 checked seven organizer records against current event-specific source evidence. The audit found **23 confirmed wrong location assignments**, **19 non-performance records**, and **24 current Comedy Shoppe listings without a matching upcoming show or ticket URL**. It also records correct assignments and unresolved evidence rather than treating every organizer feed as broken.

No production records, source configurations or scraper behavior were changed. This is a frozen read-only investigation, with implementation and data repairs delegated to TASK-4109 through TASK-4112.

## Complete accounting

Upcoming means after **2026-09-28T13:45:00Z**, fixed for every query and comparison.

| Organizer | Direct upcoming shows | Correct location | Confirmed mismatch | Unknown | Non-performance |
| --- | ---: | ---: | ---: | ---: | ---: |
| Yardbird 613 | 13 | 4 | 6 | 3 | 0 |
| Alameda 447 | 9 | 0 | 3 | 6 | 0 |
| Let's Comedy 469 | 10 | 0 | 10 | 0 | 0 |
| Comedy Shoppe 327 | 0 | 0 | 0 | 0 | 0 |
| AC Jokes 412 | 44 | 40 | 4 | 0 | 0 |
| Pagliacci 8701 | 0 | 0 | 0 | 0 | 0 |
| Big Pine 573 | 19 | 0 | 0 | 0 | 19 |
| **Total** | **95** | **44** | **23** | **9** | **19** |

There is one additional related show at hidden Let's Comedy Venues club 410. Show 1394784 has the correct White Rabbit street/city, but duplicates source event 370399 / visible-club show 1395297. Its correct location is incidental to a fixed-address JSON-LD source, not proof of functioning event-level routing.

“Correct” here means physical location, not an endorsement of the producer's display name as a venue identity. “Unknown” means the captured evidence cannot safely establish whether a reassignment is needed. “Non-performance” is separate from location mismatch: downloads and consultations should not be moved to another theater as if they were performances.

Every one of the 95 directly assigned rows has exactly one classification in the per-show files. They preserve IDs, stored URLs, dates, source evidence and the basis for each decision. Related-source searches also checked other clubs and ticket URLs; their limits are documented in the subreports.

## Findings by ingestion path

**SeatEngine — TASK-4109.** Yardbird, Alameda and Let's Comedy all use SeatEngine organizer accounts but `SeatEngineClient.create_show` assigns `club_id=self.club.id`. Event-level venue prose does not affect that choice. Yardbird has six events at Hoboken Biergarten rather than its configured Willie McBride's address. Alameda has three explicit Fireside Lounge events at 1453 Webster St rather than Central Avenue. All ten Let's events are in Indianapolis, while club 469 is in West Nyack, NY. These 19 mismatches share a demonstrated code path; they are not inferred from organizer geography alone.

Preserve Yardbird's four verified Willie McBride's dates. Three other Yardbird dates have biographies without usable venue evidence. Alameda's six Cinema Grill dates name the restaurant, but it publishes entrance 2301 Central Avenue while the parent theater complex uses the stored 2317 Central Ave. These six remain unresolved, not confirmed cross-venue errors. The repair must also reconcile the independent JSON-LD source 289 / hidden club 410 duplicate without losing existing relationships.

**Wix — TASK-4110.** The complete AC Jokes API response has 44 events, `hasMore=false`; all match stored rows by exact slug and UTC date. Forty correctly belong to the Starlight Ballroom or Directors Room at Resorts, 1133 Boardwalk. Shows 6537818, 6537828 and 6537839 belong to Hi Point Pub, 5 N Shore Rd, Absecon; show 7475796 belongs to The Cove, 3700 Brigantine Blvd, Brigantine. `WixEvent.to_show` carries location.name as room but retains the configured club. Do not replace Resorts' address or split its two rooms into unrelated physical venues. Public detail URLs returned 404, but the successful Wix API provides current positive evidence; those 404s are not cancellation evidence.

**SeatEngine product filtering — TASK-4111.** Big Pine's 19 stored rows consist of six digital downloads, five digital review services, three consultations, four workshop sessions/passes and one multi-city networking game. Individual source dates match the stored rows. The generic festival JSON-LD address is not an event venue for these products. Source 360 has empty filtering metadata; existing SeatEngine title-pattern support should be evaluated before adding another general classifier. A comedy-keyword filter alone would still admit products that use comedy vocabulary. [The classification reconciliation](big-pine/classification.md) explains why the visible festival row is intentional and why platform targets must be preserved.

**Obsolete ShowSlinger source / current PunchUp calendar — TASK-4112.** Comedy Shoppe has no upcoming assigned shows. Source 617's widget is empty, but its official socials page contains 24 unique future PunchUp events at seven locations in NJ, PA and SC. There are 23 Tixologi links and one OvationTix link. An exact comparison of all 24 URLs against all upcoming show URLs and associated ticket purchase URLs returned zero matches. This establishes an observed coverage gap, not 24 existing misassigned rows or an exhaustive title-based duplicate search. The existing shared PunchUp extractor returns only 20 entries from the captured page and omits venue identity from `PunchupShow`; simply switching the source would leave completeness and routing defects.

**Eventbrite organizer routing — no Pagliacci repair.** Pagliacci's official site redirects to a collection containing historical Cafe Italiano and Manor Grill events dated 2023/2025. They are not upcoming. The public organizer payload explicitly reports zero upcoming events, no further page and no loading failure. Wider DB searches found no relevant upcoming rows elsewhere. The configured Eventbrite organizer code already groups by expanded venue and calls `event.to_show(venue_club)`. No current evidence justifies changing its address, reassigning shows or replacing that routing path. Recheck when a new event appears.

## Repair tasks and safeguards

| Task | Deliverable | Scope |
| --- | --- | --- |
| 4109 | Route the three SeatEngine organizers and reconcile 19 confirmed mismatches | SeatEngine client/pipeline, scoped regression fixtures, source/data migrations and audit evidence |
| 4110 | Route AC Jokes by its Wix location and repair four assignments | Wix event/pipeline, scoped regression fixtures, source/data migrations and audit evidence |
| 4111 | Exclude Big Pine non-performance inventory and safely clean its audited rows | SeatEngine filtering/configuration, regression fixtures, migrations and audit evidence |
| 4112 | Recover the complete Comedy Shoppe calendar with physical-venue routing | Comedy Shoppe/PunchUp extraction, regression fixtures, source migrations and audit evidence |

Each task has three acceptance criteria, including a pinned regression test and later live verification. Durable context atoms 738–741 point to the exact evidence and code entry points. Duplicate checks found no existing task covering these same repairs. No execution dependency is required: the four tasks have independent outcomes, even where source-scoped SeatEngine changes share files. Existing task 4077 concerns generic venue name/city collisions, not this proven configured-organizer assignment behavior.

Before any future production repair, refresh source evidence and verify the current row's source, URL, date and venue. Resolve destination club identity using full address and location, not name alone. Inventory tickets, lineups, saved-show references and other dependencies; preserve recoverable before-images and stable identities wherever possible. Use transaction/count guards and record applied versus held IDs. Do not infer cancellation from absence, delete unknown-location events, bulk geocode a producer, or hide an organizer before its shows are routed visibly. Preserve reconciliation caps and incomplete-feed guards. The newly created tasks carry these requirements; the current artifacts are not executable deletion instructions.

## Evidence and verification

- `organizers.json` and `assigned-shows.json`: all seven configurations and 95 direct upcoming assignments; access-code query parameters redacted.
- `yardbird-alameda/`: 22 individual event comparisons and first-party venue-address evidence.
- `lets-shoppe/`: 11 Let's rows including the related club, 24 current Shoppe events joined to seven venues, source configuration and the exact global show/ticket URL check.
- `ac-pag/`: full 44-event Wix projection and joins; explicit empty Pagliacci organizer payload and dated historical collection evidence.
- `big-pine/`: all 19 classified rows, historical classification reconciliation and intentional platform-target ownership snapshot.
- `manifest.json`: hashes for all input JSON and expected accounting totals.
- `replay.py`: standard-library offline verification of hashes, complete identity coverage, source URL/date/venue joins, source pagination/empty states and classification totals.

Run from the repository root:

```sh
python3 apps/scraper/docs/audits/2026-09-28-organizer-venues/replay.py
```

Replay passed. Negative checks on temporary copies rejected a missing classification, a changed Wix source date even with refreshed hashes, and an altered payload with a stale hash. It checks the frozen evidence, not continued truth of live pages. Public sources were fetched using the scraper's HTTP stack; raw pages and temporary access tokens are outside the committed audit. The seven-organizer task does not expand into the separate UP/Second City identity concern attached as background context from TASK-4055.
