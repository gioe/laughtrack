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

The repair will recheck the full venue cohort and schema under locks, require an
exact reviewed before-image, save private recovery, and refuse rollback after any
affected-state drift. PostgreSQL regressions precede production execution.
