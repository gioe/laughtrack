# TASK-4139 — Barrel Room and Phoenix identity investigation

Read-only investigation on October 8, 2026. No production records changed.
Fresh native responses, exact URLs, timestamps, response digests and selected
public identity fields are in [evidence.json](evidence.json).

## Supported findings

| Source | Native API response for configured number | Operative classic source |
| --- | --- | --- |
| 77 / club 88, Barrel Room Portland | 324: Bridgeport; API website fails TLS hostname validation | Current Barrel Room events page links Eventbrite; classic extractor yields zero candidates |
| 134 / club 129, StandUpLive Phoenix | 336: Summer of Sass Inaugural Fundrasier; API website fails DNS | Phoenix classic events page returns HTTP 200 and 82 extracted candidates |

These are genuine API-name disagreements, but neither number is used by the
configured `seatengine_classic` scraper to choose its target. Its
`collect_scraping_targets` reads the source URL; `get_data` parses that HTML.
No numeric replacement is established or needed to explain that runtime path.

The original migration
`apps/web/prisma/migrations/20260319000001_backfill_club_ticketing_ids/migration.sql`
explicitly obtained these numbers from CDN asset URLs: 324 for club 88 and 336
for club 129. `apps/scraper/SCRAPERS.md` documents that CDN storage identifiers
and API venue identifiers are different namespaces, and classic scraping ignores
the numeric field. Querying the API with those metadata values therefore cannot
validate the classic source's identity. This provenance explains the observed
disagreements without asserting a historical API reassignment.

## Barrel Room evidence chain

The configured [venue events page](https://www.barrelroompdx.com/events) links
directly to Eventbrite organizer 80388668013 and several event ticket pages.
The [organizer profile](https://www.eventbrite.com/o/barrel-room-80388668013)
identifies Barrel Room PDX and its structured `sameAs` links back to
`https://www.barrelroompdx.com/`. The linked
[Open Jam and Games event](https://www.eventbrite.com/e/open-jam-and-games-tickets-1993993047883)
also links organizer 80388668013 and identifies the Portland location. This
reciprocal domain/platform linkage supports a current Eventbrite association;
it is stronger than a name match or a reachable page.

A separately indexed [classic platform page](https://www-barrelroompdx-com.seatengine.com/)
still returns Barrel Room's domain and address in structured data, plus 36
extractable candidates. This supports a legacy classic-platform association,
not current ticket validity or an approved replacement scrape URL. Its extracted
show links point back at the venue domain, which now serves a different site.
Current Eventbrite offerings include music/jam programming; this audit does not
classify every event as comedy or establish complete inventory parity.

## Phoenix evidence chain

The [parent domain](https://www.standuplive.com/) redirects to
`https://phoenix.standuplive.com/`. The configured events page and a separately
indexed [SeatEngine calendar](https://phoenix-standuplive-com.seatengine.com/calendar)
both expose structured Place identity linked to the Phoenix domain and
50 W. Jefferson St, Phoenix, AZ. The native classic extractor yields 82
candidates from the configured page. These cross-domain links and structured
location fields support the classic Phoenix association independently of the
API number 336. They do not establish a replacement API venue ID or constitute
a full persistence scrape.

## Historical leads and limits

`docs/audits/task-3498-purge-wrong-seatengine-venue-shows.json` records historical
persisted URLs with API venue 339 for club 88 and 351 for club 129. That audit's
misleading `source_id` field denotes the configured numeric venue metadata, not
the source row ID. Its skip decision used name-token overlap, which is not
independent identity proof. These are historical leads only: neither candidate
was adopted or certified as a current replacement. No API IDs were enumerated.

The native API requests used `geo.client_for` and `fetch_venue_details` with
configured authentication. Every public HTML request used the scraper's HTTP
stack and explicit accept-only headers, without API authorization. Search
results supplied additional page leads; conclusions use directly fetched HTML
and parsed structured fields. Full HTML remains a local scratch capture;
the committed evidence omits headers, cookies, private rows and long descriptions.
