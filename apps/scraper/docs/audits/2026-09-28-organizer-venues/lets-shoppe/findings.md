# Let's Comedy and The Comedy Shoppe — TASK-4065

Read-only production snapshot, fixed upcoming cutoff **2026-09-28T13:45:00Z**. Public pages retrieved 2026-09-28 13:52:09–13:52:13 UTC using the scraper's `HttpClient.fetch_html` with curl-cffi. No scraper run, production write or repair was performed. The consolidated audit created repair tasks 4109 and 4112.

## Row accounting

| Scope | Upcoming rows | Correct physical location | Confirmed mismatch | Unknown |
|---|---:|---:|---:|---:|
| Let's Comedy club 469 | 10 | 0 | 10 | 0 |
| Related Let's Comedy Venues club 410 | 1 | 1 | 0 | 0 |
| The Comedy Shoppe club 327 | 0 | 0 | 0 | 0 |

Every stored row is recorded in `per-show.json`. All ten club469 shows are in Indianapolis: nine at White Rabbit Cabaret, one (Brian Posehn, show2760604 / source376767) at Fountain Square Theatre. Club469 instead stores 4210 Palisades Center Dr A-401, West Nyack NY. Where an event supplies only the White Rabbit name, its street address is corroborated from other explicit White Rabbit events in the same collection; the mismatch already follows from the event's own Indianapolis venue/title evidence. Fountain Square's street address was not supplied and is not invented.

Club410 show1394784 (Olivia Carter, source370399, 2026-10-09 23:00Z) already has the correct White Rabbit street/city (1116 Prospect St, Indianapolis IN). This is **not proof of dynamic venue routing**: club410 is an organizer alias fixed to that address, is hidden (`visible=false`), and duplicates club469 show1395297 by source ID/time. Preserve/account for it during any later reconciliation rather than blindly moving all producer rows or counting it as another mismatch.

## Ingestion causes

- Let's source547 is enabled `seatengine`, seatengine_id444, assigned club469. `scrapers/implementations/api/seatengine/scraper.py:67-79` uses that venue ID to fetch shows. `core/clients/seatengine/client.py:59` calls `/api/v1/venues/{venue_id}/shows`; `create_show` at line192 assigns `club_id=self.club.id`. Room extraction does not change physical club. Event-specific locations in public prose do not affect assignment. Updating the configured source URL alone cannot fix venue routing.
- The public Let's JSON-LD is misleading at the structured level: each event's `location` repeats “Let's Comedy” with blank street/locality/region. Actual venue appears in event title/description. A later fix must avoid trusting empty organizer-level location metadata.
- Let's source289 is enabled `json_ld`, club410, same first-party collection. `core/entities/event/event.py:109` assigns `club_id=club.id`; its currently correct Olivia location is incidental to club410's fixed address, not a per-event resolver. Moving Brian Posehn there would still be incorrect.
- Shoppe source617 remains enabled `show_slinger`, club327 (167 Bleecker St, New York NY). `scrapers/implementations/venues/the_comedy_shoppe/extractor.py:52-103` extracts title/date/ticket ID but no event location. `transformer.py:38-45` assigns every event to `self.club.id`. Thus this path has latent organizer-routing risk, but there are **zero current upcoming rows to call misassigned**.

All code paths above are relative to `apps/scraper/src/laughtrack/` in this worktree.

## Shoppe's current feed and coverage boundary

The configured ShowSlinger widget responds successfully with “Tickets are not on sale now. Please come back soon!” and zero event cards. By contrast, `https://www.jjcomedy.com/socials` serves public PunchUp page data with **24 upcoming shows** (23 Tixologi ticket URLs and one OvationTix ticket URL), and seven physical locations in NJ, PA, and SC. Sanitized event IDs, date/times, ticket links, venue IDs and addresses are in `public-source-projection.json`; no full React payload, biographies, contact records, or backend user IDs were retained.

The public locations are Big Shots Restaurant & Lounge (Woodbridge Township NJ), Mauch Chunk Opera House (Jim Thorpe PA), Arcadia Clubhouse (Myrtle Beach SC), Newtown Theatre (Newtown PA), Dreamers Restaurant (Moncks Corner SC), Wonders Theatre (Myrtle Beach SC), and Bloomsburg Theatre Ensemble (Bloomsburg PA). This proves the organizer is not a single NYC room; it does not by itself establish that any stored upcoming show is wrong.

Discovery checks included all upcoming rows assigned clubs327/410/469, all upcoming URLs containing letscomedy/showslinger/jjcomedy, plus all upcoming Tixologi/comedyshoppe URLs and exact current Shoppe venue names. A subsequent exact-match query at 2026-09-28 14:32:32 UTC checked all 24 ticket URLs against **all upcoming shows.show_page_url and tickets.purchase_url across every club**, including the OvationTix URL `https://ci.ovationtix.com/36052/production/1262681` (Emo Philips at Wonders Theatre). It returned **zero matches**. Query scope and result are retained in `public-source-projection.json` under `database_exact_url_check`. This is evidence of an obsolete source/coverage gap and no observed already-correct Shoppe path, **not an exhaustive cross-platform title-based duplicate guarantee**. The separate Let's410 record is the one observed already-correct location in this investigation.

## Existing PunchUp implementation check

The shared `core/clients/punchup/extractor.py` is reusable; there is no generic registered PunchUp scraper in the inspected tree. A read-only run of `PunchupExtractor.extract_shows` on the captured Shoppe HTML returned **20 shows**, whereas decoding and deduplicating the complete public Flight payload yielded **24 distinct source event IDs**. A migration therefore needs full list/pagination validation (see `scrapers/implementations/venues/side_splitters/scraper.py` pagination implementation), not just a configuration swap. `PunchupShow` currently drops venue_id/venue/address and its `to_show` uses the supplied club; retain and resolve per-event locations before assignment. This is an existing-platform extension plus Shoppe source migration, not a need to invent a new ticketing platform client.

## Proposed next step, not executed

A future implementation should model producer ownership separately, route each event to its actual physical venue, retain provenance, and reconcile the source370399 duplicate. Let's needs prose/title location extraction or another reliable event-level source because JSON-LD locations are blank. Shoppe needs a current PunchUp/Tixologi source before routing can be validated. Do not bulk change organizer addresses to one current venue; both producers publish across multiple physical rooms.
