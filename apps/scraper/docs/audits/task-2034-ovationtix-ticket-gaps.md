# TASK-2034: OvationTix Ticket-Row Gaps

## Scope

Audit future active visible OvationTix shows that have no `tickets` rows, with
Side Splitters Comedy Club called out by the task.

## DB Findings

The audit query joined active visible `clubs`, enabled `scraping_sources` with
`platform = 'ovationtix'`, future `shows`, and missing `tickets` rows. It found
one affected club:

- `club_id`: 1056
- `club`: Side Splitters Comedy Club
- `scraping_source_id`: 219
- `ovationtix_id`: 35578
- `source_url`: `https://web.ovationtix.com/trs/cal/35578`

Affected future shows:

| show_id | show_name | date_utc | production_id | performance_id |
| --- | --- | --- | --- | --- |
| 1532141 | James McCann | 2026-05-28 23:00:00+00 | 1265158 | 11761427 |
| 1097975 | Mark Normand | 2026-07-23 23:00:00+00 | 1093071 | 11719480 |
| 1097976 | Mark Normand | 2026-07-24 01:30:00+00 | 1093071 | 11778932 |
| 1097977 | Mark Normand | 2026-07-24 23:30:00+00 | 1093071 | 11719482 |
| 1097978 | Mark Normand | 2026-07-25 02:00:00+00 | 1093071 | 11719483 |
| 1097980 | Mark Normand | 2026-07-26 00:00:00+00 | 1093071 | 11719484 |
| 1097981 | Mark Normand | 2026-07-26 02:30:00+00 | 1093071 | 11719485 |
| 917406 | Ben Bankas | 2026-11-20 01:00:00+00 | 1216993 | 11740811 |
| 917407 | Ben Bankas | 2026-11-21 00:30:00+00 | 1216993 | 11740813 |

## Root Cause

The generic OvationTix scraper successfully discovers the productions and
performance IDs, and the persisted shows have stable OvationTix purchase URLs.
The gap is in ticket extraction when the upstream Performance endpoint returns
no priced sections.

For affected performances, `Performance({id})` returns:

- `sections: []`
- `hasRegularPrice: false`
- `seatsForSale: false`
- `priceRange: { min: null, max: null }`
- `availableToPurchaseOnWeb: true`

Normal Side Splitters performances return populated `sections[].ticketTypeViews`
and produce ticket rows as expected.

Before this task, `OvationTixEvent._extract_tickets()` only emitted tickets from
priced `ticketTypeViews`. When OvationTix withheld price tiers for a future
performance, the scraper persisted the show but produced no ticket row, even
though the show still had a useful purchase URL.

## Resolution

Add an OvationTix fallback ticket when no priced tiers are available but the
performance has an event URL. This mirrors existing fallback behavior in other
scrapers: preserve the purchase URL with a `General Admission` row and mark it
sold out when the upstream availability flags are not ticket-available.

## Verification

Focused entity tests cover:

- No OvationTix sections produces one fallback ticket.
- Existing priced OvationTix sections continue to produce tier-specific tickets.

Command:

```bash
/Users/mattgioe/Desktop/projects/laughtrack/apps/scraper/.venv/bin/python3 -m pytest tests/core/entities/test_ovationtix_event.py
```

Result: `2 passed`.
