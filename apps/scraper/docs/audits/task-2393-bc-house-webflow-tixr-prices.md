# TASK-2393: BC House Webflow Day-Card Depth and Tixr Prices

Date: 2026-05-22

## Scope

Audit House of Comedy British Columbia's generic Webflow day-card scraper for
two questions:

- Whether the homepage day cards represent the full available inventory, or
  whether pagination / item discovery is missing events.
- Whether stable source data exposes actual Tixr ticket prices instead of only
  purchase URLs.

## Source Configuration

Live DB source row:

| club_id | club | platform | scraper_key | source_url | metadata |
| --- | --- | --- | --- | --- | --- |
| 2357 | House of Comedy British Columbia | custom | tixr_webflow_day_card | https://bc.houseofcomedy.net/ | `tixr_group_fragment=tixr.com/groups/comicstripbc/events/` |

The active scraper is
`laughtrack.scrapers.implementations.api.tixr.scraper.TixrWebflowDayCardScraper`.
It fetches the venue homepage and parses `a.day-card` links whose `href`
contains the configured Tixr group fragment. It does not call Tixr detail pages
or the Tixr group API.

## Inventory Findings

Live homepage fetch through the scraper stack on 2026-05-22:

- Homepage HTML length: `59,640` bytes.
- `day-card` class occurrences: `36`.
- Parsed events matching `tixr.com/groups/comicstripbc/events/`: `18`.
- `TixrWebflowDayCardScraper.get_data(...)` therefore returns 18 events.

Persisted future DB state at the same time:

| metric | count |
| --- | ---: |
| Distinct future shows | 18 |
| Ticket rows | 18 |
| Ticket rows with `price IS NULL` | 0 |
| Ticket rows with `price = 0.00` | 18 |
| Ticket rows with `price > 0` | 0 |

The 18 parsed live homepage URLs matched the 18 persisted future show URLs:

```text
https://www.tixr.com/groups/comicstripbc/events/todd-ness-187893
https://www.tixr.com/groups/comicstripbc/events/todd-ness-187895
https://www.tixr.com/groups/comicstripbc/events/todd-ness-187897
https://www.tixr.com/groups/comicstripbc/events/todd-ness-187898
https://www.tixr.com/groups/comicstripbc/events/april-macie-174093
https://www.tixr.com/groups/comicstripbc/events/april-macie-174094
https://www.tixr.com/groups/comicstripbc/events/april-macie-174095
https://www.tixr.com/groups/comicstripbc/events/april-macie-174096
https://www.tixr.com/groups/comicstripbc/events/april-macie-174097
https://www.tixr.com/groups/comicstripbc/events/jessimae-peluso-174104
https://www.tixr.com/groups/comicstripbc/events/jessimae-peluso-174105
https://www.tixr.com/groups/comicstripbc/events/jessimae-peluso-174106
https://www.tixr.com/groups/comicstripbc/events/jessimae-peluso-174107
https://www.tixr.com/groups/comicstripbc/events/jessimae-peluso-174108
https://www.tixr.com/groups/comicstripbc/events/ray-lau-174110
https://www.tixr.com/groups/comicstripbc/events/ray-lau-174111
https://www.tixr.com/groups/comicstripbc/events/ray-lau-174112
https://www.tixr.com/groups/comicstripbc/events/ray-lau-174113
```

Conclusion: the current homepage scraper is not missing items from the live
homepage surface. No homepage pagination or "load more" route was observed in
the scraper output path, and the current parser output count matches persisted
future rows exactly.

## Price Findings

The current Webflow day-card source does not contain price fields. It exposes
title, room, date, time, and the Tixr purchase URL only. The code path is:

- `WebflowDayCardExtractor._parse_card(...)` extracts the card fields and
  `ticket_url`.
- `WebflowDayCardEvent.to_show(...)` creates a single fallback ticket via
  `ShowFactoryUtils.create_fallback_ticket(ticket_url)`.
- After TASK-2405, `create_fallback_ticket(...)` defaults `price` to `None`
  for unknown prices, not `0.0`.

A live transformation check on 2026-05-22 produced 18 shows whose tickets all
had `price=None`, for example:

```text
Todd Ness 2026-05-22 19:30:00-07:00
[('General Admission', None, 'https://www.tixr.com/groups/comicstripbc/events/todd-ness-187893')]
```

The DB still has 18 future `price = 0.00` rows, but those rows no longer match
current scraper semantics. They are stale unknown-price fallback rows from
before the null-default change, not proof that the shows are free.

## Tixr Detail/API Findings

The Tixr group page surface exposes prices. A rendered/indexed Tixr group page
for `https://www.tixr.com/groups/comicstripbc` lists BC events with visible
price text, including:

- Todd Ness at `$26 CAD +` / `$34 CAD +`.
- April Macie at `$26 CAD +` / `$34 CAD +`.
- Jessimae Peluso at `$26 CAD +`.

That proves the public Tixr surface has price data for this venue. However, the
same stable price surface is not currently reachable from the scraper
environment:

- `make probe-tixr GROUP=comicstripbc` attempted
  `https://www.tixr.com/api/groups/comicstripbc/events?page=1`; direct
  curl-cffi returned HTTP 400, and the fallback browser/proxy path returned a
  DataDome bot-block page instead of parseable JSON.
- `TixrClient.fetch_group_events("comicstripbc")` returned zero parsed events
  for the same DataDome / no-JSON outcome.
- `TixrClient._fetch_tixr_page(...)` for
  `https://www.tixr.com/groups/comicstripbc/events/todd-ness-187893` returned a
  DataDome CAPTCHA shell, not event JSON-LD or visible prices.
- The direct event page text exposed to the web/indexed fetch did not include
  price details; the group page is the only observed public surface with
  prices.

## Disposition

Classification: **price route exists on Tixr's group page, but no currently
reliable scraper-environment route was verified for extracting it.**

Recommended actions:

1. No inventory-depth fix is needed for the current Webflow homepage path. The
   live scraper output count equals the persisted future show count.
2. Do not treat existing `price = 0.00` BC House rows as free. Current code
   emits `price=None`; the persisted zero rows should age out or be corrected by
   the next successful reconciliation path that updates the existing fallback
   ticket.
3. A price-extraction implementation would need either:
   - a reliable Tixr group API configuration for `comicstripbc` that reaches
     `sales[].tiers[].price` through `TixrClient.fetch_group_events(...)`, or
   - a new Tixr group-page parser that can safely consume the server-rendered
     group page price text and map it back to event URLs.
4. Focused regression coverage for either implementation path should assert
   that BC House day-card inventory remains 18 when the homepage fixture
   contains these cards, and that unavailable Tixr price data leaves fallback
   tickets at `price=None` rather than `0.0`.

## Evidence Commands

Live homepage extraction:

```bash
cd apps/scraper
PYTHONPATH=src .venv/bin/python3 -c '<instantiate TixrWebflowDayCardScraper for club_id=2357; fetch source_url; run WebflowDayCardExtractor.extract_events(...)>'
```

Read-only DB counts:

```bash
cd apps/scraper
PYTHONPATH=src .venv/bin/python3 -c '<query shows/tickets for House of Comedy British Columbia where s.date > NOW()>'
```

Tixr group API probe:

```bash
cd apps/scraper
make probe-tixr GROUP=comicstripbc
```

Tixr detail probe:

```bash
cd apps/scraper
PYTHONPATH=src .venv/bin/python3 -c '<run TixrClient._fetch_tixr_page("https://www.tixr.com/groups/comicstripbc/events/todd-ness-187893")>'
```
