# Execution and verification

Applied October 8, 2026 UTC after the exact reviewed plan passed a transaction
dry run and rolled back. The repair merged five proven placeholder duplicates,
corrected the retained Mainstage time, moved the retained Level 1B and Level 3B
occurrences to The Substation, and filled both verified 2027 ComedySportz rooms.
The seven retained shows use existing producer 50. A retry returned
`already_applied: true` without writes.

Across both physical venues, shows and tickets each changed from 146 to 141.
Five strictly identical ticket offers were coalesced into the retained offers;
no distinct offer was discarded. Duplicate tag links changed 256 to 244. All
2,000 ticket-click IDs and business fields were preserved, with only reviewed
duplicate show references repointed. Lineups, saved shows, notifications and
discovery snapshots were empty in this production cohort. Tests separately
exercise preservation of populated user relationships and conflict refusal.

All 134 unreviewed show rows are exactly unchanged, including both Level 2A
rows, historical Level 1B 3179544 and the remaining historical blank rooms.
Sources, producer and producer-venue links are identical before and after.
Only the clubs' show counts changed: Rozzie 135 and Substation 6.

## Public and replay verification

After refreshing the verified LaughTrack project's CDN response cache, all
original API URLs were checked without cache-busting parameters. Five retired
show IDs return 404. Seven retained IDs return 200 with reviewed venue, room and
instant; their ticket offers and booking URLs equal the saved pre-repair values.
The three held control responses are unchanged. Sanitized results and backup
hashes are in [verification.json](verification.json).

The full read-only native scraper replay fetched 137 shows without errors;
all seven repaired identities match its candidates by booking URL, venue, room
and instant. See [live-replay.json](live-replay.json). No replay inventory was
written to production. Existing source routing holds unavailable calendars,
preventing legacy list-page 09:00 placeholders from returning. Real PostgreSQL
tests exercise native extraction and ShowHandler persistence twice with batch
sizes 1 and 100, preserving the repaired canonical ID, ticket, saved show and
click reference without adding a phantom slot.

## Tests and gate limitation

47 focused tests passed with no skips after archiving the script:

```sh
TEST_DATABASE_URL=postgresql:///test_sql_parse PYTHONPATH=src:. .venv/bin/python3 -m pytest \
  tests/scripts/test_repair_anyroad_blank_rooms.py \
  tests/scrapers/implementations/anyroad/test_venue_routing.py -q
```

Seventeen repair tests cover exact merge/holds, repeat safety, serialized JSON
rollback/reapply, private backup permissions/failure, before-image drift,
physical/native/ticket/user collisions, schema changes and after-state drift.
Black, pyflakes and whitespace checks passed. The full scraper gate could not
collect because the shared environment lacks `tzdata`; Tusk's unchanged-HEAD
precheck failed identically three times with no flakiness or upstream divergence.
The documented path-limited commit fallback was used for this unrelated failure.

## Recovery

The executed one-off is archived at
`scripts/archive/repair_anyroad_blank_rooms_2026_10_08.py`. The exact plan is
[reviewed-plan.json](reviewed-plan.json). Full before/after recovery files contain
private relationships and remain outside Git with mode 0600:

- `/private/tmp/task4135-production-backup.json`
- `/private/tmp/task4135-production-backup.json.after.json`

From `apps/scraper`, restore only after reviewing current state:

```sh
PYTHONPATH=src:. .venv/bin/python3 scripts/archive/repair_anyroad_blank_rooms_2026_10_08.py \
  --plan docs/audits/2026-10-08-anyroad-blank-rooms/reviewed-plan.json \
  --restore /private/tmp/task4135-production-backup.json.after.json
```

Restore refuses changed schema, checksums or affected after-state and restores
the exact original IDs and relationships. It was verified locally, not executed
against the successfully repaired production inventory.
