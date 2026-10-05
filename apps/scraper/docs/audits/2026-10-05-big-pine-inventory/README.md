# Big Pine product cleanup — TASK-4111

Big Pine remains a visible festival identity (club 573). Source 360 remains enabled
and uses SeatEngine venue 553. The intentional platform sources 3126/7146 and
source_targets 1/2 are preserved. This is not a venue-to-producer conversion.

## Evidence and bounded scope

The September 28 audit's 19 IDs still matched their stored titles, dates, rooms,
and native show URLs on October 5. Fresh SeatEngine details confirmed all 19:
six digital downloads, five digital reviews, three consultations, four education
workshop/camp passes, and one networking game. See `evidence.json` and `native.json`.
Sixteen official product pages still carried the quoted evidence. Three older
URLs redirected to the calendar; their native details instead confirmed two
FALL CAMP workshop/panel passes and the COMEDY ASSASSINS game with revival add-ons.
Do not treat those redirects as disappearance or performance evidence.

The current API feed contains 17 products, including a new 2027 submission and
an EPK Review occurrence. Anchored, case-insensitive title exclusions in source
360 metadata cover the reviewed products and submission, tolerating surrounding
whitespace. This uses the existing title-filter contract and does not exclude
broad words such as festival, pass, camp, or comedy. Genuine festival performances
and festival admission passes remain eligible. Unconfigured sources are unchanged.

The deletion cohort is **only the original 19 IDs**, frozen in `plan.json` and the
script. All other 53 stored rows are held, including submission show 7773673 and
older product rows outside this audit. The new submission is excluded on ingestion
but was not silently added to the approved deletion cohort. `inventory.json` records
the full pre-repair public inventory. Private user/dependency before-images are
represented here only by hashes and counts, never committed as rows.

## Applied cleanup

`cleanup_big_pine_inventory.py` verifies the exact inventory and full before-image
hashes under table locks. It checks all seven inbound show foreign keys, including
CASCADE versus SET NULL behavior, and refuses new child references. A dry run
executes the same code and rolls back. Apply first writes a durable, exclusive,
mode-0600 backup, then records a full private after-image before commit.

The October 5 dry run rolled back successfully. Apply committed with these checks:

| Relation | Before | After |
| --- | ---: | ---: |
| shows | 72 | 53 |
| tickets | 74 | 55 |
| lineup_items | 9 | 8 |
| tagged_shows | 149 | 110 |
| ticket_purchase_click_events | 1063 | 1063 |
| saved_shows / sent_notifications / discovery_show_feature_snapshots | 0 | 0 |

All 417 click records linked to the deleted cohort were retained with null
show references. All other columns and held relationships were compared exactly.
The only identity-adjacent writes were source 360 metadata (plus its update-trigger
timestamp) and club 573's derived total_shows count. Visibility, other club fields,
other sources, and source targets matched their before-images exactly.

Run from `apps/scraper`, explicitly importing the active worktree source:

```sh
PYTHONPATH=src:. .venv/bin/python3 scripts/core/cleanup_big_pine_inventory.py --dry-run
PYTHONPATH=src:. .venv/bin/python3 scripts/core/cleanup_big_pine_inventory.py \
  --apply --backup /private/path/new-recovery.json
```

The applied private files are `/private/tmp/task4111-recovery.json` and its
`.after.json` companion. Keep these protected until the repair is accepted.
For recovery, lock the same tables and first compare current affected rows to the
recorded after-image, including clicks selected by their recorded IDs. Abort and
re-review any drift. In one transaction, restore the 19 show rows from `before`,
then their six cascading relationship tables, then restore the 417 click show_id
values using their unchanged click IDs. Restore source 360's original metadata and
club 573's original total_shows. Verify all business fields against the before-image;
the source timestamp trigger may advance updated_at. Never overwrite unrelated
rows or restore blindly after newer scrapes. The backup contains full rows and
column definitions to support this operator-reviewed recovery.

## Validation

The source regression reproduced the old diagnostic error: 17 filtered products
were reported as zero pre-filter items. The fix records discarded items while
BaseScraper continues to count retained items. Thus an all-filtered feed cannot
qualify as a clean empty calendar. Shared reconciliation gates and deletion caps
are unchanged.

The focused SeatEngine and PostgreSQL suite passed **46 tests**, including exact
cascades, preserved click records and held shows, source metadata preservation,
idempotence, unexpected relationships, failed backup writes, changed inventory,
changed targets, and an expanded deletion cohort. PostgreSQL fixtures use temporary
tables and always roll back; use `TEST_DATABASE_URL=postgresql:///postgres` locally.
Live scrape verification is recorded separately in `verification.md`.
