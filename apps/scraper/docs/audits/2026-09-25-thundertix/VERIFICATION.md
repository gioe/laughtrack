# TASK-4051 production verification

The full scraper commit gate passed in 71.2 seconds. Targeted repair tests passed all 25 cases against local PostgreSQL, covering exact restore, drift refusal, ticket-identity guards, cross-venue destinations, and relationship retention. Runtime/showtime tests and the 11 collision-guard tests pass; the latter exercise cross-batch rejection and the actual reconciliation gate.

## Guarded repair

A production dry run rolled back successfully, followed by the matching apply. The repair changed 32 existing show dates and retired five reviewed rows. All 8,489 original click IDs remain, with the same show links except the intended SET NULL behavior for retired rows. The 710-row pre-repair cohort became 705 rows; no unreviewed row was retired. The private recovery file is `~/.tusk/backups/laughtrack/task4051-recovery.json` (0600, fsynced before commit). It contains user relationship data and is not committed. Exact automated restore intentionally refuses drift after subsequent normal scrapes; recovery after refresh requires reviewing those later writes against the backup.

## Normal venue runs

Both runs used the normal `make scrape-club` command with task-worktree PYTHONPATH and the production database. Run type is `verify`; these are not scheduled-runner checks.

| Venue | Duration including persistence | Scraped | Saved | Inserts | Updates | Validation rejections |
|---|---:|---:|---:|---:|---:|---:|
| Visani | 41.27 s | 86 | 86 | 53 | 33 | 0 |
| Annoyance | 60.78 s | 280 | 200 | 115 | 85 | 80 |

Visani attempted 23 optional event-price lookups (16 known, seven unknown); Annoyance attempted 52 (44 known, eight unknown). Optional timeouts did not drop calendar performances. Annoyance's persistence guard rejected 40 pairs of conflicting identities before batching, and validation errors prevented automatic stale deletion. Both intentionally protected show IDs (5732294 and 4910291) retain their original title, date, room, event URL and last-scraped timestamp.

At September 25 00:50:10 UTC, Visani had 86 fresh future rows matching all 86 reviewed current source performance IDs and exact times. Annoyance had 215 future rows: 187 freshly persisted nonconflicting performances and 28 preserved older rows in collision slots. These match 215 of 263 future source performances. All 48 missing performances are explained by the known collisions; none have a mismatched time. Counts differ from the 280 fetched events because some performances became past by verification time.

This restores bounded ingestion, not complete Annoyance coverage. TASK-4081 owns the remaining identity gap. The run-level metrics record 80 validation failures and a 71.43% save rate; the legacy per-club `success=true` field reflects scrape success and does not establish complete persistence. Consumers must inspect save/validation counters.

## Scheduled follow-up

Criterion 13329 is explicitly deferred until a scheduled run uses a SHA containing TASK-4051. Verify both runtimes remain below 180 seconds, Visani inventory stays fresh, and Annoyance collisions cannot overwrite existing identities or authorize stale deletion. A run started before merge is not evidence for this change.

Public evidence is in `production-run-metrics.json`, `production-verification.json`, the reviewed plan, and source snapshots. Database row-count and identity assertions passed after both normal production runs.
