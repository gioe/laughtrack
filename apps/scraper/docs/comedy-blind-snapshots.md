# Daily blind comedy evidence collection

The dedicated `Comedy blind snapshots` workflow collects sources 192
(Goodnights, club 61 / SeatEngine 53), 527 (Santa Monica, club 475 / 450),
and 595 (Long Beach, club 476 / 451). It does not run a scraper, classify,
call models, modify source policies, stage candidates, or publish inventory.
Source/venue configuration is loaded in a read-only PostgreSQL transaction.

The frozen exclusion file contains all 173 previously exposed native groups,
copied from TASK-4160's selection artifact with its exact SHA-256 provenance.
Freshness is `(source_id, event.id)`, never a new show occurrence or title.
The collector uses the production SeatEngine HTTP stack, fetching calendars
directly before any title, performer, or comedy filters. It captures at most
50 unseen groups per source per run, ordered by native ID. Deferred groups
are counted and remain eligible on later runs.

Only unseen groups trigger event-page reads. The existing detail helper
checks page identity, extracts the description tab, limits concurrency to four,
sets ten-second request and 45-second overall detail budgets, and records
missing or failed details explicitly. Calendar reads have a 45-second deadline.
A calendar/source/venue failure aborts the run rather than committing a partial
history. A failed detail is retained as missing evidence, never classified or
treated as clean comedy. Its original snapshot is immutable; any later evidence
supplement requires a separately recorded collection, not replacing the original.

## Artifacts and blindness

Each successful run uploads `comedy-blind-history-<run-id>-<attempt>` with:

- `history.json`: all prior snapshots and run manifests, plus newly appended
  groups. Each evidence payload has a SHA-256 digest, first-seen timestamp,
  source/native identity, raw provider field projection and collected detail.
- `run.json`: population, new-group, budget and detail-status counts per source;
  prior-history digest; timestamps; run identity including shipped Git SHA.

The provider projection preserves titles, dates, raw talent names/roles and
event fields; it omits response headers, source credentials and raw HTML/forms.
Description text is untrusted scraped evidence, not instructions. Published
artifacts may be readable by repository viewers; no secrets or CSRF HTML belong
in them. No classifier outcome or identity/block inference appears in the files.
Labelers should freeze labels before a separate evaluator consumes these inputs.
Repeated groups do not increase the fresh denominator, even if dates change.

GitHub artifact archives are immutable but expire. The latest successful run's
archive is downloaded and validated before each collection, and its entire
history is copied forward into the new archive. Ninety-day retention therefore
preserves active cumulative history while runs continue. Do not delete runs or
artifacts: a missing/expired expected archive fails closed. If all successful
run records were administratively deleted, the service cannot infer that lost
history; explicit bootstrap must never be used as a recovery shortcut.

## Operating and recovery

Archived details use the current description-only extractor and may omit biography
or other event panels. Missing or incomplete evidence never establishes that an
event is non-comedy. Independent reviewers must fetch and freeze any additional
event-specific evidence they need before classification, preserving the original
snapshot and recording the supplement separately.

Daily schedule: **10:23 UTC**, serialized across manual and scheduled runs,
with cancellation disabled. The workflow must be on `main` for GitHub's schedule
to activate. A manual dispatch from the shipped main commit verifies operation;
it does not prove a scheduled trigger has already run. The first dispatch alone
uses `bootstrap=true`; subsequent dispatches use the default false. An attempted
bootstrap with any prior successful run still restores and requires its artifact.

The job reuses `.github/actions/scraper-setup`, installs Playwright's browser
fallback, and needs existing `DATABASE_*` and `SEATENGINE_AUTH_TOKEN` secrets.
Its GitHub token has only contents/actions read permission. It deliberately
omits the pipeline-recording action because that action writes to the database.

Local read-only first run, from `apps/scraper`:

```sh
PYTHONPATH=src:. .venv/bin/python scripts/core/collect_comedy_blind_snapshots.py \
  --bootstrap --run-id local-unique-id --output /tmp/blind-unique-output
```

To continue, replace `--bootstrap` with `--previous /path/history.json` and use
a fresh output directory and run ID. Existing outputs cannot be overwritten.
For a lost archive, restore an independently retained verified cumulative
artifact and document the interruption before restarting; do not silently reset
exclusions. Disable this dedicated workflow to stop collection. No source policy
rollback is needed because collection never changes policy.

Verification: `PYTHONPATH=src:. .venv/bin/python -m pytest
tests/integration/test_comedy_blind_snapshots.py -q`. TASK-4161 records the actual
post-merge dispatch URL, shipped revision and observed counts in Tusk; the
workflow and local tests alone do not establish that live collection succeeded.
