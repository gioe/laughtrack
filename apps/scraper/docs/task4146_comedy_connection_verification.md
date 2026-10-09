# Comedy Connection coverage repair (TASK-4146)

## Diagnosis — October 9, 2026

Production club 217 is Comedy Connection, 39 Warren Ave, East Providence,
Rhode Island, timezone America/New_York. No matching duplicate club or alias
exists. The venue website was the placeholder `#`.

Its sole configured source, 64, was enabled SeatEngine classic venue 14 at
`https://events.ricomedyconnection.com`. October 8–9 runs reported success with
zero shows. Production contained zero upcoming shows; the most recent stored
inventory was Natalie Cuomo on September 25–26, last scraped September 26.

The official `https://www.ricomedyconnection.com/events` calendar instead
publishes a Next.js calendar with Tixologi purchase links. Native scraper
`HttpClient.fetch_html` fetched both the calendar (422,764 bytes) and Michael
Longfellow detail (88,187 bytes). The calendar contains 48 event series and
122 performance records in its RSC data; all 48 series have rendered links.

Michael Longfellow's primary detail data contains four upcoming performances:
October 9 and 10 at 7pm and 9:30pm Eastern, with Tixologi event IDs
12821–12824 respectively. JSON-LD still includes a past October 8 performance;
the primary RSC `event.shows` list supplies the upcoming set and actual checkout
URLs. Related-event recommendations are not additional primary performances.

Chosen repair: preserve club 217, disable stale source 64, and add a native
`comedy_connection` custom source at the HTTPS official calendar. Keep historical
shows and the old source record. Join per-show JSON-LD price and performer data
by show ID; retain sold-out inventory and distinguish each performance by its
date and actual Tixologi purchase URL.

## Deployment and persisted verification

Applied the source migration after executing it twice in a transaction and
rolling back. Club 217 now has the HTTPS official website. Source 64 remains
present but disabled; new custom source 14859 is enabled. The enabled-source
geography audit has no finding for this club.

The native full scrape and subsequent `make scrape-club CLUB='Comedy Connection'`
runs returned 122 performances from 48 series. Production now stores 122 future
shows from October 9, 2026 through April 10, 2027 local time, with 122 matching
purchase URLs and 19 sold-out tickets retained. Comparing every stored UTC date
and show URL against the native extraction matched all 122 records. Multiple
runs retained the exact same show IDs (ordered-ID MD5
`2d3c0cbf5a93116224725f5d84a09390`) and empty-string rooms; no duplicate shows
were inserted. Michael Longfellow's four dates, URLs and lineup match the
official detail. No current calendar performances were excluded; past JSON-LD
entries and related-event recommendations are intentionally not ingested.

Live lineup verification found upstream JSON-LD truncations: Andre De,
Jerry Wayne and One Funny. Source metadata now maps the four affected exact
event titles to existing canonical performers André de Freitas, Jerry Wayne
Longmire, Lisa Marie and Sarper Güven. These identities have no parent or deny
entry. A compact fixture captured from the real Andre detail verifies the
upstream defect and override. Explicit lineups opt out of persistence-time
substring additions; the default for other scrapers remains unchanged.

The final production run confirmed all four corrected lineups with no extra
performers and unchanged show IDs. The three truncated comedian records created
by the first verification run were reconciled to hidden aliases of their
canonical identities, scoped by exact IDs, names and creation timestamp.
The metadata and alias migrations each passed twice-applied rollback validation
before deployment. No pre-existing comedian record was hidden or merged.

Seventeen venue regression tests cover discovery completeness, primary-event
isolation, split RSC payloads, multiple showtimes, DST/year handling, sold-out
retention, actual purchase links, malformed data, repeat identity, native
performer overrides and persistence inference. Full scraper suite is the
required commit gate; compatibility fixtures without the new optional inference
field retain the original behavior.
