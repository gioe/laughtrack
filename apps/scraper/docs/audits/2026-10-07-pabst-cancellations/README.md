# TASK-4125: explicit Pabst cancellation

## Source and reviewed cohort

On 2026-10-07 the official event page
https://www.pabsttheatergroup.com/events/detail/zarna-garg-2026
still explicitly marked Zarna Garg's October 4 Turner Hall Ballroom performance
canceled. A fresh capture through the scraper's HttpClient/curl-cffi records
event-specific `CANCELED` date and ticket controls, not the unrelated global
alert or generic cancellation/refund FAQ. See `source-evidence.json`.

Production show **3092815**, club **9120**, still had `is_cancelled=false`
after its October 3 scrape. The exact URL and Zarna/Turner Hall cohort query
returned only that row. The reviewed repair includes no other event.
Stored time is `2026-10-05T00:00:00Z` (7 p.m. Central on October 4); the detail
page says 7:30 p.m. This task preserves the stored instant and changes only
the explicit cancellation flag. No date correction is inferred.

The row has one ticket, one lineup link, one tag link, and 66 purchase-click
records. Its saved-show, sent-notification and discovery-snapshot cohorts are
empty. These references and every other show/venue field must remain exact.
Private snapshots must never be committed.

## Root cause and implementation

Pabst parsed event listing cards without consulting detail cancellation status.
A new focused test reproduced a canceled event being emitted as a scheduled
show. The implementation uses the existing cancellation-intent result channel
and guarded writer, extended narrowly to Pabst's nullable organizer identity.
Normal upserts do not clear existing cancellation flags.

Both Pabst sources review event detail pages and recent/current stored source
rows so a canceled event removed from the listing can still be recognized.
URL, title, venue and local calendar date must agree. A missing or failed
detail page produces no cancellation intent and blocks stale deletion for
that scrape. General FAQ text and unrelated global alerts are not evidence.

## Operator repair and recovery

From `apps/scraper`, after capturing fresh official HTML:

```sh
PYTHONPATH=src:. .venv/bin/python3 scripts/core/repair_pabst_cancellation.py --html /private/tmp/task4125-zarna.html
PYTHONPATH=src:. .venv/bin/python3 scripts/core/repair_pabst_cancellation.py --html /private/tmp/task4125-zarna.html --apply --backup /private/tmp/task4125-production.private.json
PYTHONPATH=src:. .venv/bin/python3 scripts/core/repair_pabst_cancellation.py --restore /private/tmp/task4125-production.private.json.after.json
```

Default dry run performs the repair, checks all captured rows, restores the
original flag, and rolls back. Apply requires a new 0600/fsynced private backup.
Restore refuses if any affected row changed since application. Only explicit
reviewed event identity can pass the repair guard; no shows are deleted.

## Verification

Production rollback-only rehearsal passed: all 69 linked records and all club
and show fields were unchanged except the cancellation flag, and restoration
reproduced the exact original state. The guarded production apply succeeded on
2026-10-07. A separate post-commit dry run reported `changed=false`, confirming
the persisted cancellation and idempotent replay with the same 69 references.

The focused Pabst, shared result-processor and PostgreSQL lifecycle suites passed
all **105 tests**, including the existing Next Stop cancellation cases. The full
scraper gate could not collect because the environment lacks `tzdata`. Tusk's
clean-HEAD precheck reproduced that failure in all three runs, with no upstream
divergence. Runtime changes were committed through the documented path-limited
fallback; no agent attribution trailer was invented when an email was unavailable.
