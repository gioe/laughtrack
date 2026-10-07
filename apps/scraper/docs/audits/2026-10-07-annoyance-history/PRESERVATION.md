# TASK-4127: no-mutation verification

No production correction was approved or executed in this investigation. All six
shows, their six tickets, and every inspected relationship remain intact. No
backup/restore operation was necessary because there was no write transaction.
The evidence here is **not** a recovery snapshot for a future repair.

`verify_history.py` opens a PostgreSQL connection with server-enforced read-only
transactions, validates the current show foreign keys against the seven known
child tables, and reads complete rows with one UNION statement per observation.
It validates six existing Annoyance show IDs and one shared native ticket identity
per pair using the existing strict ThunderTix identity parser. No scraper
persistence or repair function is called.

Two independent READ COMMITTED observations at 15:20:24 UTC on October 7, 2026
matched across every column of all six shows and **48 related records**:

| Table | 7451272 | 3769502 | 1371908 | 847662 | 1024865 | 927780 | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| tickets | 1 | 1 | 1 | 1 | 1 | 1 | 6 |
| lineup_items | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| tagged_shows | 1 | 2 | 2 | 2 | 4 | 4 | 15 |
| saved_shows | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| sent_notifications | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| discovery_show_feature_snapshots | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ticket_purchase_click_events | 1 | 26 | 0 | 0 | 0 | 0 | 27 |

`relationship-verification.json` contains public show/ticket fields, counts, and
keyed SHA-256 fingerprints of full rows. Private relationship rows never leave
process memory. The random HMAC key is discarded, so fingerprints are comparable
only between the two observations in this run. This proves net equality at those
observation points, not absence of concurrent changes that were later reversed,
and does not establish the correctness of historical dates.

Run from `apps/scraper`:

```bash
PYTHONPATH=src:. .venv/bin/python3 \
  docs/audits/2026-10-07-annoyance-history/verify_history.py \
  --output /absolute/path/to/new-audit.json
```

The committed verifier completed successfully against production read-only.
The source investigation separately parsed five historical provider calendar
arrays directly and checked the native IDs, links, dates, and timezone offsets.

The repository-wide scraper gate could not collect its tests because the shared
virtualenv lacks `tzdata`, imported by `scripts/verify_timezone_data.py`.
`tusk test-precheck --flake-retries 2` reproduced the same collection error on
unchanged HEAD in all three runs, with `pre_existing=true`,
`flaky_suspect=false`, and `diverged_from_default=false`. No runtime scraper
code was changed. The documented path-limited raw Git fallback was used; no
agent email attribution was invented where none was available.

Any later repair must take a **fresh private full-row backup**, handle duplicate
ticket/tag relationships explicitly, repoint all 27 Fire & Beer click rows
without losing their metadata, refuse unexpected schema/row drift, and verify
rollback and idempotence. The existing counts are an audit, not permission to
discard records. Preserve both God Lens shows unless new reliable evidence
resolves the exact native performance.
