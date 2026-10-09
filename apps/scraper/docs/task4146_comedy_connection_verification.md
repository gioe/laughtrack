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
