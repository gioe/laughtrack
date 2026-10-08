# TASK-4140 — Mainstage remaining occurrence times

Fresh native AnyRoad experience 88719 booking detail, retrieved 2026-10-08,
confirms November 21 and December 19 at 20:30 America/New_York at 18b Corinth
Street. Both existing production shows still have 20:00 local. The list API
09:00 schedule is a placeholder; detail availability and ISO dates agree.

| Existing show ID | Local date | Before UTC | Corrected UTC |
| --- | --- | --- | --- |
| 3179528 | 2026-11-21 | 2026-11-22 01:00Z | 2026-11-22 01:30Z |
| 3179529 | 2026-12-19 | 2026-12-20 01:00Z | 2026-12-20 01:30Z |

Decision: update only these two date fields. Preserve IDs, all other show fields,
venue ownership, tickets, user relationships, source configuration and unrelated
inventory. Both dates have a separate 18:00 ComedySportz show; neither date has
a competing Mainstage occurrence or destination-slot collision at either reviewed
venue (10970 / 61212). Exact evidence and same-day inventory appear in
[source-review.json](source-review.json).

The repair rechecks the full venue cohort and schema under locks, require an
exact reviewed before-image, save private recovery, and refuse rollback after any
affected-state drift. PostgreSQL regressions preceded production execution.


## Execution and verification

Applied October 8, 2026 after a transactionally rolled-back production rehearsal
proved exact rollback and repeat safety. [reviewed-plan.json](reviewed-plan.json)
contains the two complete show before-images and cohort hashes. Private before/
after backups are outside Git at `/private/tmp/task4140-production-backup.json`
and its `.after.json` companion, both mode 0600. They include sensitive child
rows and must remain private.

[verification.json](verification.json) proves only the two date fields changed:
141 shows, 141 tickets, 244 tags and 2,005 click events preserved, with venue,
producer, source configuration and all other relationships unchanged. A fresh
post-commit dry-run returned already_applied=true. Both public detail endpoints
returned HTTP 200 and the corrected instants; every other public detail field
was unchanged.

Two complete read-only scraper replays each returned 136 shows without error or
routing holds. Each emitted exactly one Mainstage show per native date, including
both corrected occurrences; [live-replay.json](live-replay.json) records them.
Replay output was not persisted, so no replacement shows were created.

75 focused tests passed, including 9 real PostgreSQL Mainstage tests. The full
scraper gate remains blocked at collection by missing tzdata; clean HEAD
reproduced this existing failure in all three precheck runs, with no divergence.

Recovery, from apps/scraper, only while the exact after-state still holds:

```sh
PYTHONPATH=src:. .venv/bin/python3 scripts/archive/repair_anyroad_mainstage_times_2026_10_08.py --plan docs/audits/2026-10-08-anyroad-mainstage-times/reviewed-plan.json --restore /private/tmp/task4140-production-backup.json.after.json
```

The archived script defaults to a rolled-back dry run when invoked with only
--plan. Changed relationships, inventory, source state or schema cause refusal;
review fresh evidence before taking any recovery action after drift.
