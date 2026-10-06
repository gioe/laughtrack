# TASK-4115 disposition verification

Executed 2026-10-06 with the dated script now archived at
`scripts/archive/disposition_whiplash_performer_labels_2026_10_06.py`.

## Guarded production operation

The first dry run refused changed before-images. Inspection found only background
home-location refresh timestamps on the three identities and popularity on Grand
Opening had changed. All forty reviewed associations and identity fields still
matched. New private before-images incorporated only those verified changes;
the strict guards were retained. The second dry run produced `40 -> 0` target
lineups and rolled back. Apply then committed the same result. A subsequent dry
run returned `already_applied: true` and `0 -> 0`.

Grand Opening (2353268) and Heavy Hitters (2447993) are now hidden with block
reason `task_4115_event_label`. Summer 2026 (518570) was already hidden; all of its
existing block metadata remains unchanged. No identities were deleted, aliased,
or added to the global deny-list.

The transaction compared complete before/after rows: all 40 shows, 141 tickets,
89 tagged-show rows, 217 ticket-click rows, 6 clubs, 9 scraping sources, four
other performer records, and every other reference to the three candidate
identities were preserved. Lineup rows changed from 47 to 7: exactly the forty
reviewed candidate relationships were removed. The seven other relationships
include the separate, out-of-scope Heavy Hitters Tour identity. No foreign keys
reference `lineup_items` in the inspected production schema.

## Private recovery artifacts

Full snapshots contain user-linked data and are intentionally untracked. Keep
these operator-local files available for recovery:

- `/private/tmp/task4115-identities-reviewed.json`: refreshed reviewed identities.
- `/private/tmp/task4115-associations.json`: forty source-backed associations.
- `/private/tmp/task4115-disposition-backup.json`: before-state, mode 0600;
  SHA-256 `c14db316705eae8136d86c64a4b9ab21c4b187b19580a37221959a106c59ba96`.
- `/private/tmp/task4115-disposition-backup.json.after.json`: exact after-state and
  recovery inputs, mode 0600;
  SHA-256 `df6fc5848f734dd364647d91e32a11d2fcab4adc1f7f149c0d93a0eb5a06af3c`.

From `apps/scraper`, guarded restoration is:

```sh
.venv/bin/python3 scripts/archive/disposition_whiplash_performer_labels_2026_10_06.py \
  --rollback /private/tmp/task4115-disposition-backup.json.after.json
```

Rollback refuses if any affected after-state has changed. It restores exact
identity metadata and lineup rows; it is not a blind historical overwrite.
Rollback was tested against isolated PostgreSQL fixtures, not performed against
production after the successful cleanup.

## Public verification

Read-only requests to `https://www.laugh-track.com/api/v1/` after apply confirmed:

- `comedians/2353268`, `comedians/518570`, `comedians/2447993`: HTTP 404.
- `comedians/search?comedian=<name>&includeEmpty=true`: Grand Opening and Summer
  2026 return zero results. Heavy Hitters returns only the distinct Heavy Hitters
  Tour record; none of the three reviewed identities is discoverable.
- `shows/7614186`: private grand opening show and its ticket retained, false
  performer absent.
- `shows/3846708`: Dallas showcase and its ticket retained, false performer absent.
- `shows/5656056`: Macon show retains MC Lightfoot, Adele Givens, Earthquake, and
  its ticket. ID, name, date, venue, ticket data, and source URL match the saved
  pre-cleanup API response exactly.

Public summaries are retained locally in `/private/tmp/task4115-public-after.json`.
Full database preservation covers all forty shows; public endpoint checks sample
three representative venues in addition to all three performer detail/searches.

## Regression and gate evidence

- 49 tests passed: 12 new Whiplash performer tests and 37 existing SeatEngine
  tests. Coverage exercises actual event-to-Show conversion, exact source and
  venue guards, wrong-venue holds, label-only title fallback, unchanged real
  performers/tickets/show fields, input preservation, repeated ingestion, and
  the existing hidden-name persistence filter with only database reads mocked.
- Nine PostgreSQL disposition tests passed: exact apply/preservation, idempotent
  apply and rollback, restoration/reapply, association/role/identity/canonical/
  show/source drift, reference changes preventing rollback, and backup failure
  before writes.
- The configured web commit gate failed six Canadian timezone runtime tests;
  2,448 other tests passed. Tusk's clean-HEAD precheck reproduced the failure in
  all three runs, with `pre_existing: true`, `flaky_suspect: false`, and
  `diverged_from_default: false`. The documented path-limited Git fallback was
  used. No web runtime changes were made for this scraper/database task.

The SeatEngine prevention code must reach the scraper runtime through the normal
deployment path. The production hidden-identity records already activate the
existing ingestion suppression, including for non-Whiplash sources.
