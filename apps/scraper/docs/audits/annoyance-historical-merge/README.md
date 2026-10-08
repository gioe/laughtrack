# TASK-4136: Annoyance historical duplicate repair

## Reviewed plan — October 8, 2026

Fresh ThunderTix historical calendar responses at 11:02 UTC confirm the same
exact event/performance identities established by TASK-4127. The scraper's
native `HttpClient` fetched each response and the complete JSON arrays were
parsed directly. [Source evidence](source-evidence.json) records request URLs,
capture times, decoded-body hashes, array counts and matching provider objects.

| Retire | Retain | Event / performance | Retained instant (America/Chicago) |
| --- | --- | --- | --- |
| 3769502 | 7451272 | 188918 / 3256449 | September 19, 2026, 20:00 |
| 847662 | 1371908 | 263284 / 3249429 | May 24, 2026, 18:30 |

Retained show identities, dates and descriptive fields stay unchanged, including
their null `source_performance_id`. The existing ticket-price trigger refreshes
Fire & Beer's derived `min_price` from null to 15 when its ticket price is
preserved; Spitball's free ticket leaves `min_price` null. These are provider schedule records, not evidence that
the performances actually took place. The prior Spitball venue-page disagreement
remains documented in [TASK-4127](../2026-10-07-annoyance-history/REPORT.md);
the exact native performance record determines this repair's date.

**God Lens 1024865 and 927780 are excluded.** Both show rows and all their child
rows must remain exactly equal to their fresh before-images. This task does not
resolve their disputed historical date.

The [read-only preflight](preflight-relationships.json) confirmed all six rows,
six tickets, 15 tags and 27 clicks. Saved shows, lineups, notifications and
discovery snapshots had zero rows, but remain covered by the schema, backup,
verification and regression tests. All six public show endpoints returned 200
before repair.

## Relationship conflicts and recovery

[Reviewed plan](reviewed-plan.json) pins the complete schema, six public show
before-images and full-state before/after hashes. [Relationship plan](relationship-plan.json)
lists exact ticket reconciliations and coalesced IDs. Full private relationship
rows are kept out of this audit.

The older Fire & Beer ticket 4225195 records $15; retained ticket 8491061 has
unknown price. Older Spitball ticket 782156 records $0; retained ticket 1320025
has unknown price. Within each pair the native URL, type and sold-out flag match.
Preserve the recorded non-null price on the retained ticket before coalescing
the duplicate. This preserves existing data; it does not newly verify pricing.
Any different price or other business-field conflict aborts the transaction.

Three business-identical duplicate tags coalesce. Every other relationship moves
with its ID and payload preserved. In particular, Fire & Beer's 26 old-row clicks
join the survivor's one click; all 27 IDs and all non-show fields must survive.
Venue and source rows remain unchanged.

The repair locks covered tables, refuses schema or full-row drift, writes an
exclusive mode-0600 recovery backup before mutations, then verifies the exact
modeled after-state, including ticket-derived caches, before commit. The private after-image supports guarded
exact restoration. A retry matching the reviewed after-state is a no-op; any
partial or changed state refuses. Production execution and final verification
are recorded in [verification.json](verification.json).

## Applied outcome

The corrected rehearsal matched the full expected state and rolled back. The
reviewed repair then committed in production. Independent post-commit inspection
matched every affected row to the private after-image; a retry returned
`already_applied=true` without writes. Counts changed from six to four shows,
six to four tickets, and 15 to 12 tags. All 27 click IDs and non-show fields were
preserved. Both God Lens shows, their relationships, the venue and source stayed
unchanged. The only retained show-field change was Fire & Beer's derived minimum
price becoming 15.

Public API verification returned 404 for both retired IDs and 200 for the two
survivors and both God Lens IDs. God Lens response bodies matched the preflight.

Private full-row recovery files (mode 0600) are stored outside the repository at
`/private/tmp/task4136-production-backup.json` and its `.after.json` companion.
The executed repair is archived at
`scripts/archive/merge_annoyance_historical_pairs_2026_10_08.py`.
The focused PostgreSQL suite passes **26 tests, zero skipped**, including exact
JSON backup restoration, transaction rollback, relationship preservation,
idempotence and row/schema/trigger/function drift refusal.

## Rehearsal and validation

The first production rehearsal safely rolled back because the initial model
omitted the existing ticket-price trigger's update of Fire & Beer's minimum-price
cache. A second rolled-back diagnostic confirmed that this was the sole mismatch:
show 7451272 `min_price` became 15. No rehearsal changes were committed.
The repair model and regression fixture were extended to cover the real ticket
triggers, and the schema guard includes their definitions and helper functions.

The configured full scraper gate cannot collect because the shared virtualenv
lacks `tzdata`. A clean-HEAD `tusk test-precheck --flake-retries 2` reproduced
the same error in all three runs: `pre_existing=true`, `flaky_suspect=false`,
`diverged_from_default=false`. The documented path-limited commit fallback is
used; focused repair tests remain required before application.
