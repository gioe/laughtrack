# Flop House Eventbrite offer evidence — 2026-10-05

Current feeds and details were fetched with FlopHouseJsonScraper.fetch_json
and fetch_html(skip_js_fallback=True), using the scraper's HTTP stack and
worktree source. No production writes or checkout actions were performed.

## Retained audit

The 2026-09-27 price audit retains two exact ID/date matches:

| Eventbrite ID | UTC start | USD advertised minimum | Sale expiry UTC |
|---|---|---|---|
| 2002265475938 | 2026-09-27 03:00 | 12.51 | 2026-09-27 04:30 |
| 1998162564018 | 2026-09-29 00:00 | 19.98 | 2026-09-29 01:30 |

These correspond to show/ticket 7470872/8513139 and 5647455/6397686.
The first had already ended when originally probed; both are historical
today. Two matched historical prices are the fixed-snapshot lower bound,
not two currently purchasable tickets. Tests freeze time within each sale
window and separately verify rejection after expiry.

## Current native-stack check

The current venues.json yielded two venue feeds. The first (East Village)
contained 13 future performances; two sampled Eventbrite details matched:

- CALLBACK: feed 2002584038768, startTime 1792623600000;
  https://www.eventbrite.com/e/callback-tickets-2002584038768
  — October 21 at 7 PM EDT, AggregateOffer USD 12.51 low/high.
  InStock, sale window September 29 20:49:08Z–October 22 01:00Z.
- Brooklyn Underground Comedy: feed 1997724482705, startTime 1794531600000;
  https://www.eventbrite.com/e/brooklyn-underground-comedy-tickets-1997724482705
  — November 12 at 8 PM EST, AggregateOffer USD 17.85 low/high.
  InStock, sale window August 12 16:38:24Z–November 13 02:30Z.

Event URLs gain a title slug after redirect, but retain the feed's numeric
ID. Both Event and AggregateOffer URLs and offset-aware startDate match.
Both Events are Scheduled and Offline, with explicit USD currency. Offers
represent advertised admission minima; no package or named-tier data was
provided. Do not invent a General Admission tier or fee/tax breakdown.
CALLBACK's one-item minimum is separate from ticket admission. InStock is
source-advertised availability, not a guarantee of remaining seat quantity.

These are two current matched examples, not a full coverage count. Other
feed tickets were not audited. Missing, blocked, expired, unrelated,
non-USD, package/donation or ambiguous offers remain price-unknown. No
production backfill or inventory cleanup is part of this change.
