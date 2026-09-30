# Sesh start-time reconciliation — TASK-4078

## Production recheck, September 30, 2026

All three cohorts reported by TASK-4048 now contain exactly one show, and each
matches both the current FullCalendar feed and its individual event detail
page. The feed has 24 events. Detail JSON-LD supplies explicit `-04:00` offsets;
the decorative page label says EST, but these October dates use New York daylight
time. We used the explicit offsets and the venue timezone.

| Sesh event ID | Verified New York start | Retained show | Previously reported copy now absent |
| --- | --- | --- | --- |
| AKHEJ6C3WK44AY2QJQ4QQR26 | October 2, 8:30 p.m. | 6526463 | 6867500 |
| NNHJP5XW24JYP5A5DZE2R3HI | October 16, 8:45 p.m. | 6867508 | 6526472 |
| UIWYT4R425HHOXJFWTHQYNNH | October 23, 8:45 p.m. | 6867511 | 6526476 |

All are scheduled at 55 Chrystie Street, club 16057. The source URLs, exact
timestamps, current row IDs, and aggregate reference counts are in
`2026-09-30.json`. Production queries searched the entire venue cohort by the
three URL IDs, including both host spellings, and independently checked all six
previously recorded show IDs. We did not infer why the other rows disappeared.

**No historical repair was warranted.** This task made no production writes.
The existing three tickets, six tag links, and 23 ticket-click references were
left untouched. There were no saved-show, notification, lineup, or discovery
feature-snapshot references in this bounded cohort. No user identifiers were
exported, and no rollback backup was necessary because no mutation occurred.
Any later historical repair must recheck source identity and create its private
recovery file before changing records; the old TASK-4048 mapping is not a current
repair plan.

## Reproduction and prevention contract

Although these rows already agree with the source, a persistence regression
still reproduces the underlying bug: ingesting a Sesh performance, then the
same performance URL 15 minutes later, leaves two rows. The existing room
reconciler requires an identical instant and therefore cannot preserve a show
ID through a start-time correction.

The prevention extends the existing transactional FullCalendar reconciliation
for recognized Sesh performance-detail URLs. A uniquely identified performance
may move within the same New York local date while retaining its show ID and
references. Distinct local dates, generic series URLs, ambiguous source or
stored performances, different source attribution, and occupied destinations
must not be collapsed. Ambiguity must also remain visible across batch
boundaries so stale cleanup cannot erase the records that the guard retained.

This is a bounded provider-specific identity contract, not permission to merge
arbitrary same-title shows or same-URL recurring series across dates. Changes
to another calendar provider require independent identity evidence.
