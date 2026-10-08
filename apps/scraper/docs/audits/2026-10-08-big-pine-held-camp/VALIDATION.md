# TASK-4137 validation

No repair was introduced or run. The task's no-mutation acceptance branch applies.

The committed `no-change-verification.json` records two independent read-only,
repeatable-read production observations on October 8, 2026, at 14:38 UTC.
All columns matched for 17 shows, 17 tickets, two lineup entries, 38 tags,
1,146 click records, the club, three sources, and two platform targets.
Saved shows, sent notifications, and discovery feature snapshots were empty.
Held show 522192 retained its May 10 date, one ticket and two tags.
The verifier rejects unexpected show foreign keys and asserts the previous
17-show retained cohort, visibility, source IDs and target IDs.
Private relationship rows remain in memory; the report contains keyed hashes
whose random key was discarded. Equality applies at the observation points;
it does not establish historical schedule correctness.

Focused regression command (from `apps/scraper`):

```sh
TEST_DATABASE_URL=postgresql:///test_sql_parse PYTHONPATH=src:. .venv/bin/python3 -m pytest tests/scripts/test_cleanup_remaining_big_pine_inventory.py tests/scrapers/implementations/api/seatengine/test_big_pine_inventory.py -q
```

Result: **28 passed**, no skips. Existing PostgreSQL cleanup tests exercise
the held occurrence boundary, changed dates, dependent recovery, preserved
clicks and the frozen cleanup cohort; inventory tests retain legitimate shows.
Pyflakes also passed for `verify_hold.py`.

The full scraper gate stopped during collection because `tzdata` is absent.
`tusk test-precheck --flake-retries 2` reproduced that exact failure on clean
HEAD in all three runs: `pre_existing=true`, `flaky_suspect=false`, and
`diverged_from_default=false`. The suite collected 8,169 tests before the
collection error. This is an environment limitation, not a full-suite pass.
The documented pre-existing-failure recovery used path-limited Git commits
and manual criterion completion; no dependency or runtime code was changed.
