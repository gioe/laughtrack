# TASK-3517 Thin-Coverage Chain Audit

Captured June 30, 2026 while triaging the June 29 scraping-data audit's
near-zero upcoming-show chains.

## Source Findings

| Chain | Member club | Finding |
| --- | --- | --- |
| Wicked Funny Comedy Club | Wicked Funny Comedy Club Danvers | Enabled `seatengine` source points at SeatEngine venue `641`. The live SeatEngine venue API identifies the venue as `Wicked Funny Comedy Club Danvers` but currently returns 0 shows. Source is wired and working; low count is source-side/dormant, not a scraper outage. |
| Wicked Funny Comedy Club | Wicked Funny Comedy Club Salisbury | Enabled `seatengine` source points at SeatEngine venue `642`. The live SeatEngine venue API identifies the venue as `Wicked Funny Comedy Club Salisbury` and currently returns 1 show (`Frank Santorelli at The Hungry Traveler`). Source is wired and working; low count is accurate to the source. |
| The Setup | The Setup LA | Enabled `setup` source points at the LA Google Sheets CSV tab. Live CSV has 7 rows total and 1 future ticketed row; scraper returns 1 show. Low count is accurate to the source. |
| The Setup | The Setup SF | Enabled `setup` source points at the SF Google Sheets CSV tab. Live CSV has 32 rows total and 11 future ticketed rows; scraper returns 11 shows. Low count is accurate to the source. |
| The Setup | The Setup Seattle | Enabled `setup` source points at the Seattle Google Sheets CSV tab. Live CSV has 9 rows total and 3 future ticketed rows; scraper returns 3 shows. Low count is accurate to the source. |
| The Setup | The Setup Vancouver | Enabled `setup` source points at the Vancouver Google Sheets CSV tab. Live CSV has 3 rows total and 1 future ticketed row; scraper returns 1 show. Low count is accurate to the source. |
| The Grisly Pear | The Grisly Pear Greenwich Village | Enabled `json_ld` source fetched the calendar page, but listing-page JSON-LD stayed on June/current rows while the same server-rendered HTML contained future `/events/...YYYY-MM-DDHHMMSS` anchors. Added `grisly_pear` listing scraper and migration; live probe returns 100 future/current rows for Greenwich Village/Classic titles. |
| The Grisly Pear | The Grisly Pear Midtown | Same source defect as Greenwich Village. Added `grisly_pear` listing scraper and migration; live probe returns 32 future/current rows for Midtown titles. |

## Implementation Decision

Only Grisly Pear needed a code/config fix. The generic `json_ld` scraper was
not changed because the site-specific failure is that the page contains many
useful event anchors outside the stale JSON-LD payload. A venue-specific scraper
now parses dated `/events/` anchors directly from the calendar listing, derives
the local show datetime from the URL suffix, and separates the two clubs by
title text:

- `The Grisly Pear Midtown` keeps titles containing `Midtown`.
- `The Grisly Pear Greenwich Village` keeps titles containing `Greenwich Village`
  or `Grisly Pear Classic`.

The Setup and Wicked Funny were left on their existing enabled sources because
live source probes matched the sparse persisted counts.
