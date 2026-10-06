# District Dome quarantine execution — TASK-4117

Applied on 2026-10-06 using the archived guarded repair script. Club 554 is hidden,
classified `non_comedy`, and has an accurate District Dome description. Its active
status and physical identity, including ZIP 85050, remain unchanged. Source 87 is
disabled and retains native SeatEngine venue 534, its URL, and prior metadata;
`task_4117_disposition` records the decision and previous business fields.

No shows or references were deleted, reassigned, or cancelled. The source still
lists show 291128/event 104497 with eleven inventories and no cancellation time.
The stored show 522028 retains its 2027-06-05 00:30 UTC date regardless of the
2024-looking text in its title. The separate Carry On club 600/source 336 and all
Google deny lists were untouched.

## Preservation and recovery

`repair-receipt.json` contains only counts and hashes, with identical before/after
show and reference hashes: one show, eleven tickets, three tags, 28 click records
(the same records indexed by both club and show FK), and 154 scraper-run club
references. Every direct club/show FK was discovered from PostgreSQL, locked,
and included in the exact before/after comparison. The source update timestamp
is excluded from equality because the database refreshes it automatically.

Private files, mode 0600, are retained locally and must never be committed:

- `/private/tmp/task4117-before.json`: reviewed full before-image.
- `/private/tmp/task4117-recovery.json`: full restoration backup saved before writes.

The production dry run completed with `PLAN: rolled back`; the apply completed
with `COMMITTED`. Repeated application recognizes the after-state. PostgreSQL
regressions cover idempotence, exact rollback, existing-backup refusal, and refusal
when postal/source/show/ticket/click/scraper-reference data changes.

Rollback from `apps/scraper`:

```bash
PYTHONPATH=src:. .venv/bin/python3 scripts/archive/quarantine_district_dome_2026_10_06.py \
  --rollback /private/tmp/task4117-recovery.json
```

Rollback deliberately refuses when later business rows or references differ;
review such drift rather than overwriting it. The script restores only the three
club fields and source enabled/metadata values, then checks the entire snapshot.
