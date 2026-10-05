# TASK-4106: iO Crowdwork occurrence identity

Distinct event URLs can describe simultaneous performances in an unspecified
room. The old venue/date/room key discarded one of these performances.
The existing nullable `source_performance_id` infrastructure now identifies an
opted-in Crowdwork occurrence by SHA-256 of the exact event URL and UTC instant.
The public room remains empty. Exact URL/date duplicates share one identity.

Activation is per source via strict boolean metadata `source_performance_identity`.
Only iO source 45 is activated here. Before activating another existing source,
backfill its reviewed, ticket-verified Crowdwork rows in the same transaction as
the metadata switch. Otherwise a refresh could insert a second identified row
beside an unidentified row. Do not run an older scraper build against an activated
source. URL aliases are not guessed; URL changes require reviewed reconciliation.

## Guarded backfill

`plan.json` captures all 1,686 Crowdwork-owned rows and source metadata. The 148
other historical rows are excluded. Run from `apps/scraper`:

```sh
PYTHONPATH=src:. .venv/bin/python3 docs/audits/2026-10-05-crowdwork-identity/repair.py
PYTHONPATH=src:. .venv/bin/python3 docs/audits/2026-10-05-crowdwork-identity/repair.py --apply --backup /private/tmp/task4106-identity-backup.json
```

Default execution rolls back. Apply requires a new mode-0600 private backup.
The transaction locks shows, sources and all seven relationship tables; checks
schema, source/row cohort, ticket URLs and plan age; assigns identities; then
proves existing show fields and every relationship are unchanged. The repair
marker rejects reapplication. TASK-4081 already installed the required indexes.

Both dry run and apply preserved 1,834 shows, 1,834 tickets, 3,065 lineup rows,
5,485 tags and 14,975 click records. Saved shows, notifications and discovery
snapshots were empty. The stale-delete cap remains 10; no reconciliation runs.

Immediate recovery before any subsequent writer changes these rows:

```sh
PYTHONPATH=src:. .venv/bin/python3 docs/audits/2026-10-05-crowdwork-identity/repair.py --restore /private/tmp/task4106-identity-backup.json
```

Restore requires the exact after-state and schema. Once verification or a scrape
inserts/refreshes performances, restore refuses: prepare a new reviewed recovery
plan retaining both performances and new references. Do not clear identities or
disable the flag blindly: simultaneous rows cannot fit the old unique slot key.
Private backups contain user data and must never be committed.

## Verification

80 focused tests passed, including PostgreSQL isolated-schema tests for both
feed orders, batch sizes 1/100, duplicate URL/date input, UTC equivalence, stable
IDs and ticket/saved-show/click references across refreshes.

```sh
TEST_DATABASE_URL=postgresql:///postgres PYTHONPATH=src:. .venv/bin/python3 -m pytest tests/core/entities/show/test_crowdwork_identity.py tests/core/entities/show/test_source_performance_identity.py tests/scrapers/implementations/api/test_crowdwork_scraper.py tests/scrapers/implementations/api/crowdwork tests/scrapers/foundation/crowdwork -q
```

The full scraper gate fails during collection because the shared virtualenv
lacks `tzdata`. Clean HEAD reproduced this in 3/3 runs without upstream divergence.

`verify_live.py` converts the two exact October 2 occurrences from a native HTTP
feed capture. Default mode reads only. Explicit `--apply --backup <private-path>`
uses real ShowHandler validation and SQL, binding its handlers to one transaction
to restore the missing performance and refresh both in reverse order. It checks
stable IDs, empty rooms and preservation of existing relationships before commit.

Live apply retained Paranormal Laughtivity ID **480923** and restored People
Being Funny as **7934410** at **2026-10-03 02:30 UTC** (October 2, 21:30 Chicago).
First pass: one insert, one update. Reverse-order second pass: zero inserts, two
updates. Both rooms are empty; all existing relationships survived. The original
feed SHA-256 was `a2c33ee96f7ddb0d04d5f1c3e8b26d8167f04e9994ecb1314f4f5d8d098ac3eb`.
`source-pair.json` retains the two source entries for reproducibility. Private
backups are `/private/tmp/task4106-identity-backup.json` and
`/private/tmp/task4106-pair-backup.json`.
