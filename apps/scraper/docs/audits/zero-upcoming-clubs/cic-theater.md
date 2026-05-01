# CIC Theater

## DB Snapshot

| Field | Value |
|---|---|
| Club ID | 190 |
| Name | CIC Theater |
| Address | 1422 W Irving Park Rd |
| Website | https://www.cictheater.com |
| Show listing URL | https://www.cictheater.com/browse-shows |
| Location | Chicago, IL, US |
| Status | active |
| Visible | true |
| Club type | club |
| Timezone | America/Chicago |
| Total shows | 0 |
| DB show rows | 0 |
| Upcoming shows | 0 |
| Last show | never |

## Scraping Sources

| Platform | Scraper key | External ID | Source URL | Enabled | Priority |
|---|---|---|---|---|---:|
| eventbrite | eventbrite | 34074498445 | https://www.eventbrite.com/o/cic-theater-34074498445 | true | 0 |

## Current Assessment

Eventbrite is no longer a valid source for CIC Theater's current schedule. The configured Eventbrite organizer returns zero live public events, and the Eventbrite event links still present on the website resolve to completed 2021-2022 events.

The venue website does show current activity, but it is not exposed through the generic Squarespace event API. The homepage says CIC currently runs free shows on Wednesdays and Thursdays at Finley Dunnes Tavern while it prepares a new home. The "Browse All Shows" page is stale/inconsistent: it says shows are at The Western Bar & Kitchen, links to the same empty Eventbrite organizer, and links to completed Eventbrite events.

Implemented recommendation: use a CIC-specific scraper rather than the generic `squarespace` scraper. The custom scraper reads `https://www.cictheater.com/browse-shows`, recognizes CIC's recurring Wednesday/Thursday public schedule, and generates a bounded set of upcoming dated show instances. The club address still needs review separately because the DB address is the old Irving Park location, while current site copy references newer host locations.

Web search conclusion: keep `https://www.cictheater.com/` as the main website URL. For scraper/source investigation, use `https://www.cictheater.com/browse-shows` as the relevant show-listing URL. Search results and third-party venue pages still identify `www.cictheater.com` as CIC Theater's website. The Western Chicago's comedy page says it is "Home to CIC Theater" and links users to the CIC website, so The Western appears to be a host/location reference rather than a replacement website.

## Investigation Checklist

- [x] Verify the venue website still represents an active comedy/improv venue.
- [x] Verify the Eventbrite organizer has upcoming live events.
- [x] If Eventbrite has events, check whether they are comedy-relevant and why the scraper is not ingesting them.
- [x] If the source has moved, identify the current ticketing/listing platform.
- [x] Run the scraper implementation against the live source URL after the scraper change.
- [x] Record the final action and evidence in this note.

## Notes

- Initial reason for audit: active, visible club with zero upcoming shows as of 2026-05-01.
- Investigation timestamp: 2026-05-01 18:31 EDT.
- Current DB config:
  - `scraping_sources.platform`: `eventbrite`
  - `scraping_sources.scraper_key`: `eventbrite`
  - `scraping_sources.external_id`: `34074498445`
  - `scraping_sources.source_url`: `https://www.eventbrite.com/o/cic-theater-34074498445`
- Eventbrite organizer API check:
  - Endpoint: `https://www.eventbriteapi.com/v3/organizers/34074498445/events/`
  - Params: `status=live`, `order_by=start_asc`, `only_public=true`, `expand=ticket_availability`
  - Result: `0` events, `has_more_items=false`
- Website fetchability:
  - Scraper Playwright browser successfully fetched `https://www.cictheater.com`.
  - Fetched HTML length: `98,351` bytes.
  - Homepage title: `Improv Comedy Shows and Classes in Chicago - CIC Theater`
- Source URL distinction:
  - Main website URL: `https://www.cictheater.com/`.
  - Show-listing/source investigation URL: `https://www.cictheater.com/browse-shows`.
  - Legacy alias `https://www.cictheater.com/new-folder` currently renders the same page as `/browse-shows`, but `/browse-shows` is the cleaner URL to track.
- Web search:
  - Primary result: `https://www.cictheater.com/` (`Improv Comedy Shows and Classes in Chicago - CIC Theater`).
  - CIC homepage says to follow `@cictheater` for upcoming show and class information.
  - The Western Chicago comedy page says it is "Home to CIC Theater" and links to `https://www.cictheater.com/`.
  - Theatre In Chicago lists CIC Theater's website as `www.cictheater.com`.
- Homepage source evidence:
  - Shows current free shows on Wednesdays and Thursdays at 8pm.
  - Current location text: `Finley Dunnes Tavern 3458 N Lincoln Ave`.
  - Move notice says CIC is preparing a new home at `4301 N Western Ave`, opening date TBD.
  - Advises following Instagram for upcoming show and class information.
- Show page source evidence:
  - `https://www.cictheater.com/browse-shows` and `https://www.cictheater.com/new-folder` render the same page.
  - Page title: `Browse All Shows — CIC Theater`.
  - Page text says shows are at `The Western Bar & Kitchen 4301 N Western Ave`.
  - Page links "View all upcoming shows" to the configured Eventbrite organizer.
  - Page contains five Eventbrite ticket links:
    - `165184111123` — Princeton New Money Ass Clowns' Night of a Thousand Nights, completed, 2021-08-06 to 2022-05-27.
    - `165717699099` — Pimprov!, completed, 2021-09-04 to 2022-05-28.
    - `166013285205` — FELT, completed, 2021-08-15 to 2022-05-29.
    - `165717987963` — CIC Saturday Night Showcase!, completed, 2021-08-08 to 2022-05-29.
    - `276194805097` — The Blue Hour, completed, 2022-03-05 to 2022-05-07.
- Squarespace API check:
  - The `Browse All Shows` page exposes Squarespace collection ID `615dd75dd101ee3f0d8b04e9` with collection type `10`.
  - `GetItemsByMonth` returned `0` items for May, June, and July 2026.
  - Older checks for August 2021, September 2021, March 2022, and May 2022 also returned `0` items.
- Source conclusion:
  - Current `eventbrite` scraper is accurately returning zero because Eventbrite has no live events.
  - Generic `squarespace` scraper would also return zero because the Squarespace event collection API has no dated items.
  - The scraper switch uses a CIC-specific static/recurring schedule approach rather than a platform-only config change.
- Implementation:
  - Added scraper key `cic_theater`.
  - Added source files under `apps/scraper/src/laughtrack/scrapers/implementations/venues/cic_theater/`.
  - Added event model `apps/scraper/src/laughtrack/core/entities/event/cic_theater.py`.
  - Replaced the old CIC Eventbrite smoke test with CIC custom scraper coverage.
  - Added Prisma migration `apps/web/prisma/migrations/20260501184000_switch_cic_theater_to_custom_scraper/migration.sql`.
  - Migration disables the stale Eventbrite source and enables `platform='custom'`, `scraper_key='cic_theater'`, `source_url='https://www.cictheater.com/browse-shows'`.
- Verification:
  - `cd apps/scraper && .venv/bin/python -m pytest tests/scrapers/implementations/venues/cic_theater/test_pipeline_smoke.py tests/scrapers/implementations/test_transformer_registration.py -q` passed: 27 tests.
  - Direct live scraper invocation against `https://www.cictheater.com/browse-shows` returned 16 generated upcoming shows.
  - First generated shows: `BYOT` on 2026-05-06 at 8:00 PM and `Open Stage hosted by Da 3 Jokers` on 2026-05-07 at 8:00 PM, both with room `The Western Bar & Kitchen`.
