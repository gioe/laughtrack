# TASK-4124: The Clubhouse event identity

## Evidence and cohort

Read-only production checks on 2026-10-07 found exactly one show at club 8828
or with a Next Stop `/events/the-clubhouse-` URL: show **7123739**.
It is attached to **The Clubhouse**, 1607 N Vermont Ave, Los Angeles CA 90027.
No existing New Hyde Park club was found by Clubhouse name or Denton address.
Other Clubhouse-named venues are unrelated and are not repair candidates.

The event source is
https://www.nextstopcomedy.com/events/the-clubhouse-2026-10-24-8-pm.
A fresh fetch through the scraper's HttpClient/curl-cffi on 2026-10-07 returned
92,758 bytes (SHA-256
`af7e7dcc57f17d517711748203480d6589c9ec79781c71936f350630b443ec46`).
Its ComedyEvent structured data identifies 377 Denton Ave., New Hyde Park,
NY 11040, starting `2026-10-24T20:00:00-04:00`.
The official venue website, https://www.theclubhouseny.com/, independently
corroborates 377 Denton Avenue, New Hyde Park NY 11040. HTTPS returned 200.

The stored instant `2026-10-25T00:00:00+00:00` is already correct. The stored
source URL, scraper `next_stop_comedy`, and organizer IDs 35 corroborate the
event identity. Ticket 8110440 is General Admission, $27, with that same URL.
There are two tag links and no lineup, saved-show, notification, discovery
snapshot, or purchase-click rows in the captured cohort. Private backup files
must not be committed, even when today's cohort has no user-linked rows.

## Decision

Create **The Clubhouse (New Hyde Park)** with the verified New York address,
ZIP and `America/New_York` timezone. Keep the Los Angeles club's identity and
all metadata unchanged, including its existing hidden flag and timezone.
Those existing values are not evidence that the venues are identical.

The global club-name uniqueness constraint requires a qualified canonical
name. A verified alias **The Clubhouse**, scoped to New Hyde Park/NY, lets the
existing location-first venue resolver select the New York club on replay.
Venue creation and aliasing live in the Prisma migration, per convention 20;
the separate guarded repair changes only show 7123739's `club_id`.
No show IDs, dates, tickets, tags, user references, or historical click
attribution are rewritten. No additional scraper source is needed because
Next Stop's existing organizer source owns the event.

The repair must refuse changed source/target/alias evidence and collisions,
be safe to rerun, and retain a private before/after recovery file. Restore
returns only the show's venue assignment and leaves the legitimate New York
venue and alias in place. It must refuse if affected data changed after apply.

## Verification

All 23 isolated PostgreSQL tests passed. They execute the real Prisma migration
and alias-normalization trigger, rerun both migration and repair, exercise every
reference table with nonempty synthetic records, reject evidence drift and
collisions, and verify exact restoration. The real location lookup SQL resolves
the unqualified name in New Hyde Park to the new venue only.

A production rollback-only rehearsal applied the migration and repair twice,
restored the original assignment, compared every captured row, and rolled back.
The subsequent apply at `2026-10-07T01:26:46Z` created club **92123** and moved
show **7123739** from **8828** to **92123**. The complete operation took 1.88
seconds; an independent read confirmed the after-state. The replay was a no-op.
See `production-receipt.json`. Prisma's migration ledger was not manually edited;
the idempotent migration remains safe for normal deployment.

The public endpoint `/api/v1/shows/7123739?audit=4124-after` returned club 92123,
377 Denton Avenue, the original UTC instant and the unchanged $27 ticket.
The one ticket and two tag links were unchanged; all LA club columns matched
their before-state. Existing LA timezone/count metadata was deliberately retained.

The exact private recovery files are `/private/tmp/task4124-production.private.json`
and its `.after.json` companion (0600). Recovery, from `apps/scraper`:

```sh
PYTHONPATH=src:. .venv/bin/python3 scripts/core/repair_clubhouse_identity.py --restore /private/tmp/task4124-production.private.json.after.json
```

Restore refuses subsequent affected-state changes and retains the separate NY
venue/alias. The private files must be retained for recovery and never committed.
`source-evidence.json` records a second fresh capture at 01:26:12Z (dynamic HTML
hash differs from the initial exploration fetch), including structured event
evidence and the official venue URL. Raw HTML copies are temporary evidence only.

The full scraper commit gate could not collect tests because the shared virtualenv
lacks `tzdata`. `tusk test-precheck --flake-retries 2` reproduced the same error
on unchanged HEAD in all three runs, with no upstream divergence or flake signal.
The task used the documented path-limited Git recovery; focused PostgreSQL
verification remains the passing regression evidence. No unrelated dependency
or test changes were made.
