# Sesh location reconciliation — TASK-4048

## Findings

On September 24, 2026, club 16057 had 13 same-title/same-time pairs
split between `140 Eldridge - SESH Comedy` and `55 Chrystie - SESH Comedy`.
Twelve pairs shared a performance URL. The thirteenth required independent
inspection: its two URLs represent different performances, not duplicates.

The current FullCalendar feed contains 28 events with 28 distinct detail URLs,
all at 55 Chrystie. Sesh is the only enabled FullCalendar source in production.
The feed has no separate external ID; the `event-detail.php?id=` URL identifies
the performance. Public evidence is recorded in `source-evidence.json`.

The detail pages establish two separate September 25 performances:

| Event ID | Current local time | Canonical show | Stale copies |
| --- | --- | --- | --- |
| VKXCPHUZYZ3LCQ7HOVOR2LJC | 8 p.m. | 6670869 | 6029205 |
| K37YUZEWA5WKBHQGHIJ6JAKU | 8:30 p.m. | 6085452 | 6029206, 6085453, 6670870, 6867495 |

The first detail page explicitly links to the second as a separate time.
Consequently, merging the original different-URL pair would erase a genuine
performance. Instead, each obsolete copy maps to its own current performance.

The March 14, 2027 event BSV2ZNJW3DJSCVB7WRPK7B6K is absent from the current
feed, but its detail page still advertises 9:30 p.m. at 55 Chrystie. Its room
duplicate can therefore be consolidated without assuming feed absence means
cancellation.

## Bounded repair

The reviewed mapping consolidates 16 stale records into 13 existing canonical
performances: 11 ordinary room copies, four obsolete K37 copies, and one VKX
copy. The dated repair script contains exact IDs, URLs, dates, titles, rooms,
source and venue guards. Unexpected cohort or schema changes abort the repair.

All seven referencing tables are covered by a private before/after recovery
file. User identifiers are not included in this committed audit. Restore checks
that the affected data still exactly matches the repair's post-state; subsequent
scrapes or user activity require manual reconciliation before rollback.

Production application succeeded September 24, 2026. A subsequent guarded
dry-run found no remaining work. Counts are recorded in
`production-verification.json`: shows 29 → 13, tickets 29 → 13, lineup links
14 → 7, tags 44 → 19, and ticket clicks 299 → 299. Duplicate child links were
consolidated; there were no saved shows, notifications, or feature snapshots in
the affected cohort. The recovery file is private (0600) at
`~/.tusk/backups/laughtrack/task4048-recovery.json`.

Nine isolated PostgreSQL repair tests cover reference preservation, exact
restoration, repeat execution, identity/schema drift, notification conflicts,
backup protection and failed-backup rollback.

## Prevention and remaining scope

FullCalendar room reconciliation requires a verified Sesh performance URL,
the same club and instant, and an unambiguous match. It preserves the existing
show ID and its references when moving the room. Generic calendar/homepage and
series URLs do not authorize a move. Additional providers require an explicit
identity contract. Separate dates and simultaneous performances remain distinct.
Room moves and the show upsert share a transaction. Conflicting physical keys
are rejected before batch deduplication; ambiguity and persistence errors block
stale-show deletion so cleanup cannot undo the identity guard.

TASK-4078 tracks reschedule prevention and three additional upcoming time-drift
cohorts: AKHEJ6C3WK44AY2QJQ4QQR26 (6526463/6867500),
NNHJP5XW24JYP5A5DZE2R3HI (6526472/6867508), and
UIWYT4R425HHOXJFWTHQYNNH (6526476/6867511). Those rows are outside this repair.
