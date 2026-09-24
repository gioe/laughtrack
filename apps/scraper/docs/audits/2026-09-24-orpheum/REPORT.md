# TASK-4047: Orpheum event-city repair

Verified September 24, 2026 against live production and Ticketmaster Discovery.

## Source evidence and cohort

The original audit found six upcoming URLs. Refreshed investigation found those
six plus one past event (Comedy Bang! Bang!, September 19). Fifteen stored rows
represented seven performances: eight stale wrong-city copies and seven correct
copies. Seven stale copies were upcoming; one was past. This repair covers the
exact seven reviewed URLs, not a heuristic sweep of similarly named events.

Live Discovery responses verify the five upcoming Los Angeles performances at
842 S. Broadway and Ilana Glazer at 203 W. Adams Street, Phoenix. The official
[Comedy Bang! Bang! tour page](https://comedybangbangworld.com/tour/) links the
exact past Ticketmaster event URL and lists Los Angeles, September 19, 7 p.m.
That local time is 2026-09-20T02:00Z. Source details are in source-evidence.json.

Phoenix's embedded venue ID KovZpZAE7F6A differs from the stored alternate ID
ZFr9jZedA1. Actual location-scoped matching resolves both to club 27901. Los
Angeles uses KovZpa3uCe / club 11385; Minneapolis remains KovZpakSUe / club 2861.
No Minneapolis performance was moved to another city.

| Canonical show | Stale copies | Verified UTC start | Venue |
|---|---|---|---|
| 6897100 | 3313105, 3399346 | 2026-10-15 02:00 | Phoenix 27901 |
| 3398812 | 2841348 | 2026-09-20 02:00 | Los Angeles 11385 |
| 3398813 | 2841349 | 2026-10-17 02:00 | Los Angeles 11385 |
| 3398814 | 2841350 | 2026-10-17 04:45 | Los Angeles 11385 |
| 3398815 | 2841351 | 2026-10-18 03:00 | Los Angeles 11385 |
| 3398816 | 2841352 | 2026-10-25 03:00 | Los Angeles 11385 |
| 3398817 | 2841353 | 2026-11-14 03:00 | Los Angeles 11385 |

## Repair and recovery

Applied scripts/core/repair_orpheum_show_cities.py after a complete transactional
dry run. It guards canonical/stale row shapes, geographic identities, external
source IDs, unexpected URL copies, and the set of show foreign keys. It locks
the relevant tables briefly while snapshotting and mutating, so a concurrent
saved-show or notification insertion cannot be lost through cascade deletion.

| Related records | Before | After |
|---|---:|---:|
| Shows | 15 | 7 |
| Upcoming shows | 13 | 6 |
| Lineup entries | 14 | 7 |
| Tickets | 15 | 7 |
| Show tags | 32 | 15 |
| Purchase clicks | 579 | 579 |
| Saved shows | 0 | 0 |
| Sent notifications | 0 | 0 |
| Discovery feature snapshots | 0 | 0 |

All 579 click records retain their IDs and attributes, with stale show references
repointed to the canonical performance. Canonical ticket metadata wins duplicate
ticket-type conflicts; unique lineup/tag associations are retained. No affected
saved-show or notification references existed. Integration tests additionally
exercise those cases: saved-show associations merge with the earliest save date;
notification IDs/grouping survive, and conflicting delivery identities abort
instead of silently dropping history. Wrong-location feature snapshots would be
archived rather than reused at a different venue.

Full before/after snapshots and per-show task_4047_dispositions were saved before
commit to a private mode-0600 file and copied to persistent local storage:
`~/.tusk/backups/laughtrack/task4047-recovery.json`. The archive contains analytics
identifiers, so it is intentionally excluded from git. Use the script's
`--restore <private-file>` option for recovery. Restore requires the affected
rows to still match the exact post-repair snapshot; subsequent scrape changes
require manual reconciliation, not an overwrite. A second production dry run
made zero changes.

## Prevention and validation

The historical venue metadata repair did not reconcile existing shows. A second
defect remained: Ticketmaster's INSERT ON CONFLICT(name) fallback could return a
same-named club in another city. Actual PostgreSQL tests reproduced that failure
and a missing-location misassignment before the fix.

Stable Ticketmaster IDs now precede fuzzy matching. New same-name cross-city
venues receive a city/state-qualified name. Name conflicts must corroborate
nonempty city and state, including conflicts with already-qualified names;
ambiguous collisions fail closed. Existing stable-ID names remain unchanged.

The exact acceptance-test path now contains PostgreSQL behavior tests. Tests
also cover notification preservation, saved-show collisions, exact restoration,
changed-canonical refusal, unknown copies, recovery file permissions, and a
subsequent-change recovery refusal. PostgreSQL tests use TEST_DATABASE_URL and
skip when no integration database is configured.

Six fresh full Discovery payloads were passed through the actual national
scraper and real ClubHandler SQL in one transaction with unconditional rollback.
All five Los Angeles events resolved to 11385 and Phoenix to 27901; every UTC
start matched the source. See ingestion-verification.json for precise results.

After repair, the actual ShowHandler item builder and BATCH_INSERT_SHOWS SQL
were exercised twice for those six freshly fetched events on the same rollback
transaction. Both passes returned the same existing six canonical IDs with
operation_type=updated. All seven audited URLs still had exactly one row with
the verified venue/time. No row changes were committed by this verification
(PostgreSQL sequences may advance on conflict-handled inserts). This validates
show persistence; the full ShowService child-table pipeline was not rerun.
