# TASK-4107: bounded Sports Drink cleanup

Fresh native HttpClient/curl-cffi checks on October 5 revalidated all 85 original
TASK-4064 candidates. Explicit primary cancellation CTAs remain on all 56 canceled
records. All 28 other legacy URLs still redirect directly to their recorded
Tixologi replacements. Show 506917 remains an unresolved 404 and is held.

Only future occurrences are retired: **77 rows (51 canceled, 26 rescheduled)**.
The eight holds are **506911, 506912, 506913, 506914, 506915, 506916, 506917,
506920**. All eight have elapsed; 506917 also has an explicit unresolved hold.
The exact 77 retire IDs and all 28 preserved replacement IDs are in
`manifest.json`; per-row decisions and primary CTA snippets are retained in
`decisions.json` and `pages.json`. Both stored rows for legacy event 652837 remain
separate decisions. All current replacement URL/time pairs for the 26 future
reschedules occur in the fresh listing and match their stored IDs exactly.

`listing-cards.html` contains sanitized source cards, replayed through the actual
extractor. `before.json` contains public show identity fields and source settings.
Raw pages and private relationship snapshots are excluded from version control.

## Dry run and impact

The guarded dry run selected exactly 77 of 614 venue rows, leaving 537. It proved
all retained shows, all 28 replacements, the eight holds, source settings and
retained relationships unchanged. The targeted dependent rows comprise 77 tickets,
3 lineup rows, 202 tags and 136 click records. No saved shows, sent notifications
or discovery snapshots reference a retired row. Tickets/lineups/tags cascade;
click records survive with only show_id set NULL by the existing foreign key.
The normal stale-delete cap remains 10.

Run from apps/scraper:

```sh
PYTHONPATH=src:. .venv/bin/python3 docs/audits/2026-10-05-sports-drink-cleanup/replay.py
PYTHONPATH=src:. .venv/bin/python3 docs/audits/2026-10-05-sports-drink-cleanup/cleanup.py --export /private/tmp/task4107-dry-run-backup.json
```

The second command defaults to rollback and requires a new private export path.
The recorded dry-run before-image is `/private/tmp/task4107-dry-run-backup.json`
(mode 0600). Apply adds `--apply` and requires another exclusive export filename.
Schema/FK validation, table locks, exact current identities/freshness, all replacement
and hold identities, source settings, dependency counts, current future dates and
24-hour evidence age are checked before deletion. Any drift rolls back. Existing
backup paths are never overwritten. Each click's remaining fields are compared
exactly after deletion; the venue's total_shows aggregate is refreshed.

## Recovery

Private exports contain the original venue row, full show/source rows, all seven
relationship tables, schema snapshot, manifest digest and exact retired IDs. Do
not commit them. To recover, first lock the same tables and verify schema and
that retired IDs and legacy venue/date/room keys remain vacant. Restore only the
retired shows under their original IDs, then their tickets, lineup and tag rows.
Reattach each exported click only if its current show_id is NULL and every other
field still equals its before-image. Never overwrite changed/new records or
restore the whole venue snapshot over a later scrape. Refresh the venue count,
advance affected serial sequences above max(id), and compare restored rows and
relationships against the before-images before committing. Any drift requires a
new reviewed recovery plan rather than blind restoration.

## Regression and subsequent scrape

Historical evidence replay and 76 focused tests passed (Sports Drink pipeline,
result processor, stale reconciliation handler). TASK-4108 separately owns the
2099 purchase-confirmation card: the subsequent live scrape must report its
validation error honestly and retain the generic validation-error cleanup guard.
No cap override or validation bypass is part of this cleanup.

The apply completed at 19:43 UTC on October 5. `applied.json` records the exact
transaction result, and `post-apply.json` records an independent committed-state
read confirming 77 absent targets, eight retained holds, all 28 replacements and
136 intact click records. The actual recovery export is
`/private/tmp/task4107-applied-backup.json` (private, mode 0600).

The full scraper test gate is blocked during collection by missing `tzdata` in
the shared local virtualenv. Three clean-HEAD precheck runs reproduced the same
failure with no upstream divergence. The focused tests and evidence replay ran.

The subsequent live command was `PYTHONPATH=src:. make scrape-club CLUB='Sports Drink'`
on October 5 at 19:43–19:46 UTC (exit 0). It extracted119 records, updated118,
inserted0 and reported0 database errors. The one validation failure was the2099
Thank You For Your Purchase placeholder. Reconciliation correctly skipped cleanup
because persistence reported a validation error; the effective cap remained10.
`live-metrics.json` and sanitized `live-scrape.txt` preserve these results. A second
independent database check in `post-scrape.json` confirms537 stored rows,77 retired
IDs absent, all8 holds and28 replacement IDs intact, and136 click records preserved.
TASK-4108 owns the remaining placeholder filter; no guard was bypassed here.
