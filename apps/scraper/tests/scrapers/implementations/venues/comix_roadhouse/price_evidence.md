# Comix linked checkout evidence — TASK-4098

Verified October 5, 2026 through ComixRoadhouseScraper.fetch_html, using the
native HTTP stack and skip_js_fallback=True for optional checkout requests.
Read-only source checks; no production ticket backfill or checkout submission.

The retained September 27 venue audit matched exactly two existing unknown
tickets, not the entire Comix inventory:

| Show / ticket | Leap checkout slug | Performance (UTC) | USD base admission |
| --- | --- | --- | --- |
| 3467852 / 3876257 | spinnato-magic-sept2026aa1d6mtc | September 27 21:00 | GA 15, VIP Reserved 25, Front Row 35 |
| 3467871 / 3876276 | heather-shaw-092726fjuef5h | September 27 23:00 | GA 15, VIP Reserved 25 |

Full URLs use https://events.leapevents.com/event/<slug>. Each retained Event.url,
Offer.url and canonical URL agree. Event.startDate carries -0400 and matches the
venue's local performance time. Offers are named primary admission, USD,
InStock, with explicit validFrom/validThrough windows ending at showtime.
The fixed-snapshot recoverable lower bound is two tickets; remaining unsampled
tickets are unresolved, not extrapolated recoveries.

Both historical URLs remain reachable and still expose the same offers today,
but their sale windows have expired. Their stale InStock fields must not make
them currently purchasable. The current pages omit the purchase fee disclosure.

A current listing check used /calendar/in-the-comedy-club, then
/comics/spinnato-magic-oct2026. Its October 8 17:00 America/New_York performance
links to https://events.leapevents.com/event/spinnato-magic-oct2026wuou2wt.
The checkout Event matches that URL and 2026-10-08T17:00:00-0400 exactly.
It publishes Front Row 35, VIP Reserved 25 and General Admission 15 USD,
all InStock and valid August 2 through October 8 showtime. This independently
confirms the current source shape, not another recovery from the audit cohort.

Retained and current purchasable checkouts separately state:

- .purchase_wrapper.fee_disclosure: A 15.00% SERVICE FEE will be applied to your order.
- .event-spec[data-label="Ages"]: 18+ | $10 FOOD-BEV MIN

Keep those policies separate from numeric base admission. Do not choose 10 as
the cheapest ticket, add the food minimum to admission, or invent an all-in total.
Only matched USD individual admission with a current sale window and InStock
availability can supply numeric prices. Unknown currency, packages, missing or
invalid prices and unavailable evidence remain unknown. Optional enrichment is
deduplicated by checkout URL, capped at four concurrent requests, ten seconds
per fetch and thirty seconds for the phase; same-host rate limiting still applies.
