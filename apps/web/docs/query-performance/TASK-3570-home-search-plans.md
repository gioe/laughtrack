# TASK-3570 Home And Search Query Plans

Captured against the Neon database on 2026-07-03 with:

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) ...
```

## Catalog Signal

`pg_stat_user_tables` showed the hot high-scan tables that motivated the task:

| table        |  seq_scan |    seq_tup_read | n_live_tup |
| ------------ | --------: | --------------: | ---------: |
| lineup_items | 6,665,975 | 202,314,538,890 |     79,447 |
| tickets      |   174,058 |  19,972,066,937 |    111,339 |
| comedians    | 1,929,512 |  11,001,848,209 |      8,500 |
| shows        |    30,005 |   2,156,889,227 |     96,014 |

## Show Availability Predicate

Representative query: upcoming show search page, ordered by `date ASC, id ASC`,
`LIMIT 20`, visible clubs, excluding title sold-out markers and fully sold-out
ticket sets.

Before:

- Runtime: 197.5 ms
- Plan shape: `Index Scan using shows_date_idx`, but startup was dominated by
  two hashed subplans over `tickets`.
- Ticket work:
  - `Seq Scan on tickets` for all ticket rows: 111,339 rows, 33.0 ms
  - second `Seq Scan on tickets` for unsold rows: 107,271 rows, 53.1 ms

After:

- Query code filters `shows.tickets_sold_out = false`; the column is maintained
  by ticket triggers and backfilled in migration
  `20260703172048_add_show_tickets_sold_out`.
- The equivalent plan no longer touches `tickets` for availability filtering;
  it keeps the `shows_date_idx` early-return shape for the page query.
- Measured runtime with the ticket relation removed from the predicate: 0.8 ms
  for the same `LIMIT 20` shape.

Count path:

- Before: 354.8 ms for `COUNT(*)` over future visible available shows, including
  two full `tickets` scans.
- Correlated ticket-only rewrite test: 222.9 ms.
- Measured with the ticket relation removed from the predicate: 215.9 ms.
  Remaining work is the future-show date range plus visible-club join.

Home weekly rail:

- Before: 97.1 ms for the next-seven-days popularity rail, including two full
  `tickets` scans.
- Measured with the ticket relation removed from the predicate: 35.2 ms.

## Comedian Show Count Sort

Representative query: `/comedian/search?sort=show_count_desc`, visible parent
comedians, deny-list and restricted-tag filters, ordered by upcoming show count.

Before:

- Runtime: 309.6 ms
- Plan shape: `Seq Scan on comedians`, then 7,027 correlated count subplans.
- Hot work: 75,946 `shows_pkey` index lookups from the per-comedian
  `lineup_items -> shows` count.

After:

- Query code aggregates once with:
  - `LEFT JOIN lineup_items ON lineup_items.comedian_id = comedians.uuid`
  - `LEFT JOIN shows ON shows.id = lineup_items.show_id`
  - `COUNT(shows.id) FILTER (...)`
  - `GROUP BY comedians.id, comedians.name`
- Runtime: 133.8 ms.
- Plan shape: one `Seq Scan on lineup_items`, one filtered scan/hash of
  upcoming shows, one grouped aggregate, then top-N sort.

The grouped path keeps existing filters: deny list, restricted tags, optional
name, tag filters, home-city filter, zip/date scope, and `minUpcomingShows`
threshold via `HAVING`.
