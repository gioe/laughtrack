# TASK-2388: HAHA Comedy Club Tixr Pagination and Prices

Date: 2026-05-22

## Scope

Audit HAHA Comedy Club's custom Tixr-backed scraper for two questions:

- Whether event discovery covers the full venue/Tixr source surface.
- Whether ticket prices are available from the venue calendar, Tixr short URLs,
  Tixr detail/API data, or another stable source.

## Source Configuration

Live DB source row:

| club_id | club | platform | scraper_key | source_url | enabled |
| --- | --- | --- | --- | --- | --- |
| 163 | HAHA Comedy Club | custom | haha_comedy_club | https://www.hahacomedyclub.com/calendar | true |

The active scraper is
`laughtrack.scrapers.implementations.venues.haha_comedy_club.scraper.HahaComedyClubScraper`.
It avoids per-event Tixr fetches and parses JSON-LD Event blocks plus visible
time elements directly from the venue calendar HTML.

## Inventory Findings

The live calendar fetch through the scraper path returned:

- HTML length: `100874`
- JSON-LD Event blocks: `37`
- `HahaComedyClubScraper.get_data(...)` events: `37`

The persisted future DB sample had:

- distinct future shows: `36`
- ticket rows: `38`
- ticket rows with `price = 0.00`: `36`
- ticket rows with `price > 0`: `2`

Comparing live calendar event IDs to persisted future ticket/show URLs found:

| comparison | count | notes |
| --- | ---: | --- |
| live calendar event IDs | 37 | Parsed by the current scraper from the calendar page. |
| persisted future event IDs | 34 | Distinct event IDs in current future rows. |
| live IDs missing from DB | 3 | `188720`, `188722`, `188724` — all `OPEN MIC NIGHT` rows. |
| DB event IDs absent from live calendar | 0 | By event ID. |

The DB also contains stale/ambiguous duplicate event-ID rows by date:

- `https://tixr.com/e/177003` is persisted for both `Percy Rustomji and
  Friends - JULY 1ST` and `Percy Rustomji and Friends - JULY 8th`; the live
  calendar currently lists only `JULY 8th` for event `177003`.
- `https://tixr.com/e/188217` is persisted for `Victor By Willie` on both
  2026-06-14 and 2026-06-27; the live calendar currently lists only the
  2026-06-27 occurrence for event `188217`.

Conclusion: the current scraper parser is not missing pagination on the live
calendar page. It parses all 37 JSON-LD Event blocks currently present on the
source page. The inventory discrepancy is in persistence/state relative to the
current calendar surface: three live open-mic events are absent from future DB
rows, and two DB rows look stale or collapsed onto reused Tixr event URLs.

## Price Findings

The venue calendar JSON-LD has an `offers.price` key on every event, but every
current value is the empty string:

```text
JSONLD_EVENTS 37
PRICE_COUNTS Counter({'': 37})
```

Representative calendar offer shape:

```json
{
  "name": "JoJo Garcia: The Ten Dollar Ticket",
  "startDate": "May 30, 2026",
  "offers": {
    "@type": "Offer",
    "name": "General Admission",
    "price": "",
    "priceCurrency": "USD",
    "url": "https://tixr.com/e/188211",
    "availability": "https://schema.org/InStock"
  }
}
```

Because the HAHA scraper currently converts a missing/empty price to `0.0`,
calendar-only rows are persisted as free-looking fallback tickets even when the
event title suggests a paid show.

The live DB confirms this pattern:

- `JoJo Garcia: The Ten Dollar Ticket` (`https://tixr.com/e/188211`) persists
  one `General Admission` ticket at `0.00`.
- Most non-open-mic shows also persist one `General Admission` ticket at
  `0.00`.
- The only current non-zero HAHA ticket rows are for `Angelo Tsarouchas: The
  Diaspora Tour SPECIAL EVENT`, with old-looking Tixr long-form URLs and prices
  `49.00` (`VIP Seating Couch Seating`) and `39.00` (`GENERAL ADMISSION`).
  The current HAHA calendar scraper path does not reproduce these tiers; it
  emits only the calendar fallback row for `https://tixr.com/e/176027` with
  price `0.0`.

## Tixr Detail/API Findings

Tixr short URLs and the known Angelo long-form URL were not usable as a stable
price source from the scraper environment on 2026-05-22:

- `TixrClient.get_event_detail_from_url("https://tixr.com/e/188211")` returned
  no event after detecting a DataDome interstitial and failing to recover JSON-LD.
- `TixrClient.get_event_detail_from_url("https://tixr.com/e/185659")` returned
  no event for the same reason.
- `TixrClient.get_event_detail_from_url("https://tixr.com/e/176027")` returned
  no event for the same reason.
- `TixrClient.get_event_detail_from_url("https://www.tixr.com/groups/hahacomedyclub/events/angelo-tsarouchas-the-diaspora-tour-176027")`
  also returned no event after DataDome.
- Plain Playwright rendering reached the short URLs but the body text was empty,
  so it did not expose visible prices.
- `TixrClient.fetch_group_events(...)` against likely group IDs
  `hahacomedyclub` and `haha-comedy-club` returned zero events; the group API
  attempts hit HTTP 400/403 and DataDome fallback pages.

The generic Tixr client can extract prices when it receives Tixr event data:
`TixrClient._build_tickets_from_tiers(...)` reads `sales[].tiers[].price`.
That is the likely source of the historical Angelo paid rows. However, no
currently reachable HAHA route provides that payload reliably from the scraper
environment.

## Disposition

Classification: **price not currently feasible from a stable reachable source**.

The venue calendar is a stable event inventory source, but it intentionally
publishes empty `offers.price` values for all current events. The Tixr event
detail and group API surfaces that could expose tier prices are blocked by
DataDome or return no parseable JSON from the scraper environment.

Recommended action:

- Do not treat HAHA calendar `offers.price == ""` as evidence that a show is
  free. A future implementation should prefer `Ticket(price=None, ...)` for
  missing/empty calendar prices so the UI does not label paid-looking shows as
  free.
- Add focused HAHA scraper coverage for empty-string calendar prices to assert
  unknown price behavior.
- Add inventory regression coverage with a fixture containing multiple
  `OPEN MIC NIGHT` entries on different dates and repeated event names, so the
  parser keeps all distinct event IDs.
- Separately investigate persistence/update behavior for the three missing
  live open-mic IDs and the two stale duplicate event-ID/date rows; the parser
  itself returns all current calendar events.

## Evidence Commands

Read-only DB query used the scraper `.env` from the primary checkout and showed
36 future HAHA shows, 38 ticket rows, 36 zero-price rows, and 2 paid rows.

Live calendar verification used:

```bash
cd apps/scraper
PYTHONPATH=src /Users/mattgioe/Desktop/projects/laughtrack/apps/scraper/.venv/bin/python3 -c '<run HahaComedyClubScraper.get_data("https://www.hahacomedyclub.com/calendar")>'
```

Tixr detail verification used:

```bash
cd apps/scraper
PYTHONPATH=src /Users/mattgioe/Desktop/projects/laughtrack/apps/scraper/.venv/bin/python3 -c '<run TixrClient.get_event_detail_from_url(...) for sample short and long URLs>'
```
