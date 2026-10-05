# Showpass detail pricing — TASK-4097

Verified October 5, 2026 UTC (October 4 local) with `ShowpassScraper.fetch_json`
and `skip_js_fallback=True`. Public GET requests only; no DB updates/purchases.

The retained September 27 audit has 101 unknown tickets. Two upstream-priced
examples are CAD, so the safe USD recovery lower bound is **zero**. The remaining
99 tickets are unresolved by these samples; this is not a current inventory target.

Retained API: `https://www.showpass.com/api/public/events/1540189/`, Workshop
Open Mic, September 29 00:00 UTC. Calendar and detail IDs/dates agree. Tiers:

| Named tier | CAD base | CAD with service charges, before tax | CAD including tax |
| --- | --- | --- | --- |
| Monday Workshop - General Admission | 15.00 | 17.11 | 17.97 |
| Monday Workshop – BOGO Half-Price | 22.50 | 24.85 | 26.10 |

Fee quotes are under `fees_pricing_info.psp_web["2"]`; the payment-option key
must remain attached to its quote. 17.11 includes 2.11 service charges but
**excludes** 0.86 tax. Do not call it an all-in price or recompute fees from
overlapping component fields. Both tiers had inventory 85, sold_out false,
and sales ending September 29 03:30 UTC. GA purchase limit is 8, BOGO is 20.
BOGO description says buy one admission and get the second for half price;
`is_bundle` and `is_custom_package` are nevertheless false. Never divide 22.50.

Retained browser evidence for Adam Tiller, September 29 19:30−06, contains
CAD GA 15, Tuesday Half off Special 24.95, Dinner & Show Experience for 2 at
39.95, and for 4 at 59.95. These dinner/promotion amounts are not individual
admission minima. Their labels and units must survive without division.

Current checks:

- Historical event 1540189 still matches its name/date/currency, but returns
  zero ticket_types and `stats.is_available=false` after its sale window.
  There is no current recoverable price for that historical row.
- The Comedy Cave October calendar returned 25 rows. Its first current event
  1552733, Workshop Open Mic October 6 00:00 UTC, exactly matches
  `https://www.showpass.com/api/public/events/1552733/`. It returns the two
  named CAD tiers and amounts above (IDs 4520053/4520054), inventory 85,
  `stats.is_available=true`, and sales ending October 6 03:30 UTC. This verifies
  the live detail shape; it is not another recovered row from the fixed cohort.

Currency guard: Ticket has no currency column, and downstream prices/minima
assume USD. Keep CAD amounts explicitly labeled as CAD and numeric price unknown;
do not convert or relabel them. Only verified USD individual admission with an
open sale window and positive availability may populate numeric price. Packages,
minimum-quantity restrictions, unknown currency/availability, invalid/zero prices,
and failed detail requests remain numerically unknown. Preserve the source tier
and keyed fee evidence in the Showpass offer model. Detail fetching is optional,
deduplicated by ID per calendar batch, bounded to four concurrent requests,
ten seconds each and thirty seconds per batch. The three monthly calendar
batches remain subject to the scraper's existing orchestration and rate limiter.
