# Execution and verification

The reviewed source-only repair committed successfully on October 8, 2026.
`verification.json` records an independent live read at 18:01:49 UTC, after apply.
The live state exactly matched the saved private after-image. The only source
fields changed were `enabled` (true to false) and trigger-managed `updated_at`.
The real `ClubQueries.GET_ALL_CLUBS` selector no longer returns club 88.
Repeat execution recognized the applied state and performed no writes.

Full-row before/after comparisons preserved the club and all 323 shows, 323
tickets, 10 lineup entries, 278 tagged-show rows and 1,694 ticket-click rows.
Saved shows, sent notifications and feature snapshots were empty and remain so.
No venue/source identity, show time, URL or relationship was reassigned or deleted.
Existing shows remain visible according to their unchanged prior state; disabling
ingestion does not remove previously ingested music from the public inventory.

Private recovery files on the execution machine:

- `/private/tmp/task4142-production-backup.json` — fresh pre-write snapshot
- `/private/tmp/task4142-production-backup.json.after.json` — complete recovery

Both are mode 0600 and excluded from Git. They contain private relationship data.
Keep them with this reviewed plan while rollback may be needed. From the scraper
directory, recovery is:

```sh
PYTHONPATH=src:. .venv/bin/python scripts/archive/disable_barrel_room_source_2026_10_08.py \
  --plan docs/audits/2026-10-08-barrel-room-source/reviewed-plan.json \
  --restore /private/tmp/task4142-production-backup.json.after.json
```

Recovery is deliberately conditional on the exact affected after-state and schema;
changed inventory or relationships require a new review. It restores `enabled`
while allowing the database to refresh its source timestamp. Production recovery
was not executed; the rollback path was exercised against local PostgreSQL.

## Tests

88 focused tests passed, including all 14 new PostgreSQL recovery tests:

```sh
PYTHONPATH=src:. TEST_DATABASE_URL=postgresql:///test_sql_parse .venv/bin/python -m pytest \
  tests/scripts/test_disable_barrel_room_source.py \
  tests/scripts/core/test_repair_annoyance_identity.py \
  tests/scrapers/implementations/api/seatengine_classic -q
```

Coverage includes history preservation, repeat execution, source/history drift,
trigger timestamp handling, exact-state rollback, tampered recovery, schema/FK
changes and refusal to overwrite a recovery file. The live dry run rolled back
successfully before apply. No runtime extractor or organizer routing was changed.

The full configured suite collected 8,196 tests but failed collection in
`tests/foundation/utilities/test_timezone_data.py`: missing `tzdata`.
`tusk test-precheck --flake-retries 2` reproduced that failure on unchanged HEAD
in all three runs, with no default-branch divergence. The documented pre-existing
failure commit fallback was used; this is not a full-suite pass.
