# TASK-2417: Tixr Group ID Disposition

Date: 2026-05-23

## Scope

Audit enabled Tixr-backed scraping sources that do not currently carry
`scraping_sources.metadata.tixr_group_id`:

- Improv Asylum
- St. Marks Comedy Club
- The Stand

The goal is to determine whether each venue needs a numeric Tixr group id for
price backfill, and to resolve ids only through bounded, low-impact methods.

## Live Source Rows

Read-only query against the live scraper database on 2026-05-23:

| club_id | club | source_id | platform | scraper_key | source_url | key metadata |
| ---: | --- | ---: | --- | --- | --- | --- |
| 141 | Improv Asylum | 390 | tixr | tixr | https://www.tixr.com/groups/improvasylum | `detail_fetch_required=true`, `datadome_dependent=true` |
| 16 | St. Marks Comedy Club | 218 | tixr | tixr_public_card | https://www.stmarkscomedyclub.com/calendar | `detail_fetch_required=false`, `datadome_dependent=false`, `tixr_source_type=venue_public_card` |
| 5 | The Stand | 85 | tixr | tixr_public_card | https://thestandnyc.com/shows | `detail_fetch_required=false`, `datadome_dependent=false`, `tixr_source_type=venue_public_card` |

## Improv Asylum

Current strategy: generic `TixrScraper` over
`https://www.tixr.com/groups/improvasylum`, with a hard-coded Pixl Calendar
fallback to `https://calendar.improvasylum.com/api/events/improv-asylum`.

Price need: no numeric `tixr_group_id` is required for the current scraper
strategy. The Pixl response already contains `sales[].currentPrice` tier data,
and the scraper builds priced `TixrEvent` tickets directly from that response.

Bounded checks:

- `make probe-tixr GROUP=improvasylum LIMIT=2` attempted
  `/api/groups/improvasylum/events?page=1`; the direct request returned HTTP
  400 and the fallback path returned a DataDome bot-block page, so the slug is
  not a usable group-events API key.
- A single scraper-stack fetch of
  `https://www.tixr.com/groups/improvasylum` returned a DataDome interstitial
  (`html_len=1483`) and exposed no `/api/groups/<numeric-id>`, `groupId`, or
  `group_id` value.
- Direct fetch of the Pixl Calendar API returned a live JSON payload with
  `events`, `total`, `timezone`, and per-event `sales` tiers. A representative
  first event included ticket tiers with `currentPrice` values including
  `29.01`, `25.38`, and `33.54`.

Disposition: do not stamp `tixr_group_id`. Discovery of a numeric id remains
blocked by DataDome from the scraper environment, and the current Pixl fallback
already provides priced tickets without group-events API backfill.

## St. Marks Comedy Club

Current strategy: `tixr_public_card` over the venue-owned calendar page.

Price need: no numeric `tixr_group_id` is required for the current scraper
strategy to produce most prices today. The public-card parser extracts
Webflow-style event cards from the venue page and maps JSON-LD offer prices by
Tixr ticket URL. It does not fetch Tixr detail pages and does not call
`TixrClient.fetch_group_events(...)`.

Live parser check on 2026-05-23 returned 40 events / 40 tickets:

- `positive_prices`: 36
- `null_prices`: 4
- `zero_prices`: 0

Disposition: do not stamp `tixr_group_id` from this task. A numeric id could
be useful later if the remaining null-price cases become important, but the
current public-card route is not broadly price-blind.

## The Stand

Current strategy: `tixr_public_card` over `https://thestandnyc.com/shows`.

Price need: The Stand can remain on the venue-owned public-card route for
prices after the follow-up parser fix in TASK-2417. The Stand branch reads
`.show_row` cards, extracts date/time from the venue show URL slug, extracts
the Tixr purchase URL from `a.btn-stand`, and now reads price text from the
outer `div.ticket` container used by the current live page.

Live parser check after the parser fix on 2026-05-23 returned 18 events / 18
tickets:

- `positive_prices`: 17
- `null_prices`: 0
- `zero_prices`: 0

Bounded checks:

- The known Tixr group slug from ticket URLs is `thestandnyc`.
- `make probe-tixr GROUP=thestandnyc LIMIT=2` attempted
  `/api/groups/thestandnyc/events?page=1`; the direct request returned HTTP 400
  and the fallback path returned a DataDome bot-block page.
- User-provided Chrome NetLog
  `/Users/mattgioe/Desktop/chrome-net-export-log.json` showed
  `https://www.tixr.com/api/groups/2072` and
  `https://www.tixr.com/api/groups/2072/events?page=1`.
- `make probe-tixr GROUP=2072 LIMIT=2` returned The Stand events with priced
  `sales[].tiers[].price` values.

Disposition: do not stamp `tixr_group_id` as part of this task because the
current venue-page parser now captures prices directly. If The Stand later
needs Tixr group-events API backfill, use verified numeric group id `2072`.

## Conclusion

No metadata changes are made by TASK-2417:

- Improv Asylum's numeric Tixr id was not safely discoverable from bounded
  scraper-stack probes, and its current Pixl fallback already returns priced
  tiers.
- St. Marks Comedy Club is a venue-page public-card source with mostly complete
  JSON-LD offer price coverage from the venue page itself.
- The Stand is a venue-page public-card source for event discovery and price
  extraction after the parser fix that reads the current `div.ticket` price
  container. Its verified numeric Tixr group id is `2072`, but stamping that id
  is optional while the venue page provides prices.

Because no metadata is being changed, there is no one-shot disposition script
for this task.

## Evidence Commands

Live source-row query:

```bash
cd apps/scraper
make query SQL="SELECT c.id AS club_id, c.name, c.website, c.visible, c.status, ss.id AS source_id, ss.platform::text AS platform, ss.scraper_key, ss.source_url, ss.enabled, ss.priority, ss.metadata FROM clubs c JOIN scraping_sources ss ON ss.club_id = c.id WHERE c.name IN ('Improv Asylum','St. Marks Comedy Club','The Stand') AND ss.enabled = true ORDER BY c.name, ss.priority, ss.id"
```

Improv Asylum group-events slug probe:

```bash
cd apps/scraper
make probe-tixr GROUP=improvasylum LIMIT=2
```

Public-card live price check:

```bash
cd apps/scraper
PYTHONPATH=$(pwd)/src .venv/bin/python3 - <<'PY'
import asyncio
import json

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.tixr.scraper import TixrPublicCardScraper


VENUES = [
    {
        "id": 16,
        "name": "St. Marks Comedy Club",
        "website": "https://www.stmarkscomedyclub.com",
        "timezone": "America/New_York",
        "source_url": "https://www.stmarkscomedyclub.com/calendar",
    },
    {
        "id": 5,
        "name": "The Stand",
        "website": "https://thestandnyc.com",
        "timezone": "America/New_York",
        "source_url": "https://thestandnyc.com/shows",
    },
]


async def inspect(row):
    source = ScrapingSource(
        platform="tixr",
        scraper_key="tixr_public_card",
        source_url=row["source_url"],
        metadata={"tixr_source_type": "venue_public_card"},
    )
    club = Club(
        id=row["id"],
        name=row["name"],
        address="",
        website=row["website"],
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone=row["timezone"],
        scraping_sources=[source],
        active_scraping_source=source,
    )
    data = await TixrPublicCardScraper(club).get_data(row["source_url"])
    prices = [
        ticket.price
        for event in (data.event_list if data else [])
        for ticket in event.show.tickets
    ]
    print(json.dumps({
        "name": row["name"],
        "ticket_count": len(prices),
        "positive_prices": sum(1 for p in prices if p is not None and p > 0),
        "null_prices": sum(1 for p in prices if p is None),
        "zero_prices": sum(1 for p in prices if p == 0),
    }, indent=2))


async def main():
    for row in VENUES:
        await inspect(row)


asyncio.run(main())
PY
```

The Stand group-events slug probe:

```bash
cd apps/scraper
make probe-tixr GROUP=thestandnyc LIMIT=2
```

The Stand numeric group-events probe:

```bash
cd apps/scraper
make probe-tixr GROUP=2072 LIMIT=2
```

Improv Asylum Tixr group-page bounded fetch:

```bash
cd apps/scraper
PYTHONPATH=$(pwd)/src .venv/bin/python3 - <<'PY'
import asyncio
import re

from laughtrack.core.clients.tixr.client import TixrClient
from laughtrack.core.entities.club.model import Club


async def main():
    club = Club(
        id=141,
        name="Improv Asylum",
        address="216 Hanover St",
        website="https://improvasylum.com",
        popularity=0,
        zip_code="02113",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    html = await TixrClient(club)._fetch_tixr_page(
        "https://www.tixr.com/groups/improvasylum"
    )
    print("html_len", len(html) if html else None)
    for pattern in [
        r"/api/groups/(\d+)",
        r"groupId[^0-9]{0,20}(\d+)",
        r"group_id[^0-9]{0,20}(\d+)",
    ]:
        print(pattern, sorted(set(re.findall(pattern, html or "")))[:20])


asyncio.run(main())
PY
```
