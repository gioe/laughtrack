# TASK-2391: Laugh Boston Tixr Pagination and Prices

Date: 2026-05-22

## Scope

Audit Laugh Boston's Pixl-backed (Tixr ticketing) scraper for two questions:

- Whether event discovery covers the full venue/Tixr source surface (pagination,
  item discovery).
- Whether ticket prices are available from the venue calendar, Tixr detail/API
  data, or another stable source, and whether the existing paid-price extraction
  is complete.

## Source Configuration

Live DB source row (`scraping_sources`):

| club_id | club | platform | scraper_key | source_url | priority |
| --- | --- | --- | --- | --- | --- |
| 140 | Laugh Boston | custom | laugh_boston | https://pixlcalendar.com/api/events/laugh-boston | 0 |

The active scraper is
`laughtrack.scrapers.implementations.venues.laugh_boston.scraper.LaughBostonScraper`
(key `laugh_boston`, registered automatically by `ScraperResolver`).

Despite the venue using Tixr for checkout, the scraper does not call any Tixr
endpoint directly. It fetches a single JSON document from the Pixl Calendar API
(`https://pixlcalendar.com/api/events/laugh-boston`) and builds `TixrEvent`
objects from that response. The migration from Tixr-page extraction to the Pixl
API landed in commit `32094993d` (TASK-565, 2026-03-23) and bumped surfaced
inventory from ~10 events to >100 events while sidestepping Tixr's DataDome WAF.

## Inventory Findings

Live Pixl Calendar fetch on 2026-05-22:

- HTTP: `200`, payload `341,341` bytes after the
  `pixlcalendar.com` → `www.pixlcalendar.com` 307 redirect.
- Events returned: `120` (all future-dated; no past events in payload).
- Pagination fields in payload (`page`, `total`, `next`, `hasMore`,
  `cursor`, etc.): `0` — none present.
- `LaughBostonScraper.get_data(...)` consumes the response in a single
  `fetch_json` call (`scraper.py:51`) with no loop or offset/limit handling.

Persisted future DB sample (`shows` joined to `tickets`, `date >= NOW()`):

- Distinct future shows: `126`.
- Future shows missing tickets entirely: `0`.
- Future shows with at least one paid ticket (`price > 0`): `126` (100%).
- Ticket rows total: `168` (multiple tiers per show in some cases).
- Ticket rows with `price IS NULL`: `0`.
- Ticket rows with `price = 0.00`: `8`.
- Ticket rows with `price > 0`: `160`.

Inventory comparison:

| comparison | count | notes |
| --- | ---: | --- |
| Live Pixl future events | 120 | Single JSON fetch, all priced. |
| Persisted future DB shows | 126 | +6 versus live Pixl. |
| Pixl events with empty `sales` array | 0 | Every live event has at least one tier. |
| Pixl events with all-zero `currentPrice` | 0 | Every tier has a positive numeric price. |

Conclusion: the current scraper parser is not missing pagination on the live
Pixl response. Pixl returns the venue's full forward calendar in one payload and
the scraper consumes all 120 events. The +6 DB delta is on the persistence side
(stale future shows that have rolled off the live Pixl response), not a parser
gap.

## Price Findings

Live coverage on Pixl is complete:

```text
PIXL_FUTURE_EVENTS 120
EVENTS_WITH_PRICED_SALES 120
EVENTS_WITH_EMPTY_SALES 0
EVENTS_WITH_ALL_ZERO_PRICES 0
```

Representative event price shape from the Pixl response:

```json
{
  "id": "...",
  "title": "Ben Bankas",
  "start": "2026-07-23T23:00:00...",
  "status": "soldout",
  "price": "Check website",
  "sales": [
    {"id": 2003857, "name": "General Admisson", "currentPrice": 33, "state": "SOLD_OUT"}
  ],
  "ticketUrl": "https://www.tixr.com/e/..."
}
```

The extractor at `apps/scraper/src/laughtrack/scrapers/implementations/venues/laugh_boston/extractor.py`
reads prices in two paths:

- Sales tier path (lines 80–88) — `float(sale.get("currentPrice", 0))` per
  entry in `sales`. This is the primary path and matches all 120 live events.
- Empty-sales fallback (lines 90–97) — when `sales` is empty, emits a single
  `Ticket(price=float(event.get("price", 0) or 0), type="General Admission")`.
  Note the Pixl top-level `price` field is a string like `"Check website"` or
  `"33"`; the fallback's `float(...)` call would raise on the non-numeric form,
  so this branch effectively only emits `price=0` (or raises and is swallowed
  by the outer `except`).

### Stale `$0` General Admission rows

Eight upcoming Laugh Boston tickets are persisted with `price = 0.00`. They are
not free events. They are stale leftovers from the empty-sales fallback path
that have not been removed by subsequent successful scrapes:

```text
SHOWS_WITH_DUP_ZERO_AND_PAID 8
```

The signature is unmistakable. Every $0 row has `type = "General Admission"`
(the hard-coded fallback string at `extractor.py:96`) and `sold_out = false`.
The matching paid row on the same `show_id` has `type = "General Admisson"`
(Pixl's typo, copied verbatim from `sales[0].name`) and the correct price/
sold-out state:

| show_id | name | date | price | sold_out | type |
| ---: | --- | --- | ---: | --- | --- |
| 489821 | Ben Bankas | 2026-07-24 | 0.00 | false | General Admission |
| 489821 | Ben Bankas | 2026-07-24 | 33.00 | true | General Admisson |
| 489822 | Ben Bankas | 2026-07-25 | 0.00 | false | General Admission |
| 489822 | Ben Bankas | 2026-07-25 | 33.00 | true | General Admisson |
| 489823 | Ben Bankas | 2026-07-25 | 0.00 | false | General Admission |
| 489823 | Ben Bankas | 2026-07-25 | 33.00 | true | General Admisson |
| 489824 | Ben Bankas | 2026-07-26 | 0.00 | false | General Admission |
| 489824 | Ben Bankas | 2026-07-26 | 33.00 | true | General Admisson |
| 489859 | Amber Autry | 2026-10-09 | 0.00 | false | General Admission |
| 489859 | Amber Autry | 2026-10-09 | 30.00 / 40.00 | true | General Admisson / Premium Seating |
| 489860 | Amber Autry | 2026-10-10 | 0.00 | false | General Admission |
| 489861 | Amber Autry | 2026-10-10 | 0.00 | false | General Admission |
| 489862 | Amber Autry | 2026-10-11 | 0.00 | false | General Admission |

Mechanism: a prior scrape ran when these shows existed on Pixl but had not yet
populated their `sales` array, so the fallback emitted `Ticket(price=0,
type="General Admission")`. A later scrape with populated sales appended the
real tiers, but the stale fallback row was not removed because ticket
reconciliation is keyed on `(show_id, type)` and the Pixl typo `"General
Admisson"` does not collide with the fallback's correctly-spelled `"General
Admission"`.

This is invisible to end users today because the show-detail UI surfaces the
paid tier, but the `price = 0` rows pollute the data set for any consumer that
aggregates ticket prices (free-filter logic, price histograms, etc.).

### TASK-2405 unknown-price alignment gap

TASK-2405 standardized unknown ticket prices to `None` across the generic Tixr
client (`apps/scraper/src/laughtrack/scrapers/implementations/api/tixr/client.py`
lines 688 and 928 — JSON-LD and tier paths), SeatEngine, Ninkashi, HAHA, and
Rodneys. The Laugh Boston extractor was not updated in that refactor:

- `extractor.py:85` still uses `float(sale.get("currentPrice", 0))`, so a
  missing or null `currentPrice` becomes `0.0` rather than `None`.
- `extractor.py:92` still uses `float(event.get("price", 0) or 0)`, so an
  empty/missing top-level price becomes `0.0` rather than `None`.

Currently dormant because Pixl populates `currentPrice` for all 120 live events,
but the divergence violates the post-TASK-2405 convention and the existing $0
duplicates suggest empty-sales states do occur in the wild on this source.

## Tixr Detail/API Findings

No Tixr detail or group-API call is required for this venue. The Pixl Calendar
response already includes the full event title, start datetime, timezone,
description, ticket URL, sold-out state, and per-tier prices. The scraper
deliberately avoids per-event Tixr fetches because they trigger DataDome
challenges from GHA runners (per the docstring at `scraper.py:11`).

## Disposition

Classification: **price route exists, paid-price extraction is complete on the
live Pixl response; two follow-up gaps worth filing as separate tasks.**

Recommended actions, in priority order:

1. **Stale $0 fallback ticket reconciliation.** Cleanup of the 8 known shows
   and a fix so future empty-sales fallback rows do not persist alongside
   real paid tiers. Options include (a) deleting fallback `Ticket(price=0,
   type="General Admission")` rows for any show that also has a non-zero
   priced ticket from this scraper, (b) keying fallback writes on a sentinel
   `type` distinct from real tiers so reconciliation can replace them, or
   (c) emitting `price=None` for empty-sales fallback so the rows do not
   appear as free.
2. **TASK-2405 alignment for Laugh Boston extractor.** Update
   `extractor.py:85` and `extractor.py:92` to emit `price=None` instead of
   `0.0` for missing/null Pixl prices, matching the convention applied to
   the generic Tixr client and other scrapers in TASK-2405. Add focused
   pytest coverage for an event with `sales = []` and for a sale with
   missing `currentPrice`.
3. **No pagination or inventory regression work required.** Pixl Calendar
   returns the full venue forward calendar in one payload and the scraper
   parses it without filtering. The +6 DB-vs-Pixl delta is a persistence
   matter (stale shows rolling off Pixl), not a parser gap, and is out of
   scope for this audit.

## Evidence Commands

Source row and DB counts (read-only, via `apps/scraper/Makefile` `query`
target):

```bash
cd apps/scraper
make query SQL="SELECT scraper_key, platform, source_url, priority FROM scraping_sources WHERE club_id = 140 ORDER BY priority"
make query SQL="SELECT COUNT(*) FROM shows WHERE club_id = 140 AND date >= NOW()"
make query SQL="SELECT COUNT(*) FILTER (WHERE t.price IS NULL) AS price_null, COUNT(*) FILTER (WHERE t.price = 0) AS price_zero, COUNT(*) FILTER (WHERE t.price > 0) AS price_paid, COUNT(*) AS total_tickets FROM tickets t JOIN shows s ON s.id = t.show_id WHERE s.club_id = 140 AND s.date >= NOW()"
make query SQL="SELECT COUNT(DISTINCT s.id) AS shows_with_dup_zero FROM shows s JOIN tickets t0 ON t0.show_id=s.id AND t0.price=0 JOIN tickets tp ON tp.show_id=s.id AND tp.price>0 WHERE s.club_id=140 AND s.date >= NOW()"
```

Live Pixl verification:

```bash
curl -sL "https://pixlcalendar.com/api/events/laugh-boston" \
  -H "User-Agent: Mozilla/5.0" -o /tmp/lb_pixl.json
python3 -c "
import json
data = json.load(open('/tmp/lb_pixl.json'))
events = data.get('events', [])
print(f'events={len(events)}')
print(f'empty_sales={sum(1 for e in events if not e.get(\"sales\"))}')
"
```
