# Attic unavailable-listing audit — TASK-4079

## Disposition on September 30, 2026

All 16 rows from TASK-4049 remain at Attic club 575. Three are now historical;
13 are future listings. All 11 distinct Eventbrite IDs return authenticated
HTTP 403 with `NOT_AUTHORIZED`. Their public pages, fetched with the scraper's
own HTTP stack, display a generic unavailable page with no event metadata.
Each row is classified as **unavailable, event status unconfirmed** in
`source-evidence.json`. This distinguishes the observable availability from
an unsupported claim that the event was canceled or made private.

No event-specific source establishes a replacement date, physical venue or
cancellation. Therefore all 16 rows are retained without mutation. No user
references were changed or exported, and no rollback backup was needed. The
five two-time URL pairs remain unresolved; sharing an event ID does not tell
us which of their previously stored start times was correct.

The [official homepage](https://theatticcomedyclub.com/) and
[performer page](https://theatticcomedyclub.com/comedians) still announce the
temporary move caused by water damage. The Walrus address is 143 E Main St;
existing tickets remain valid. Oak Street will reopen on a date yet to be
announced. That general notice confirms the temporary arrangement, but does
not establish that an individually unavailable event is still happening.

Attic 575 at 892 Oak Street and Walrus 29044 remain distinct physical venues.
Both sources remain enabled. No permanent alias, blanket event move, closure
flag or cancellation flag was introduced.

## Why these rows survived

The Eventbrite organizer scraper routes events using their individual venue
objects, rather than the organizer's original address. Its organizer override
calls `EventbriteClient.fetch_all_events` directly, bypassing the normal
`BaseScraper._fetch_raw_data` path that increments successful/failed fetch
counters. HTTP status can therefore be 200 while both counters remain zero.

The latest five production Attic run records show exactly this pattern:
43 shows, success true, HTTP 200, no errors or bot block, and zero successful
or failed fetches. The latest recorded observation is 17:16:47 UTC on September
30. `ScrapingResultProcessor._is_clean_for_reconciliation` refuses deletion
when successful fetches are zero. This explains why a successful-looking
organizer refresh has not reconciled the old Attic inventory.

The default deletion cap of 10 is a second safeguard: the current 13 future
rows would exceed it even with clean diagnostics. It is not a permanent
quarantine: as dates pass, the future count changes. Raising the cap or merely
fixing the counters could expose unresolved rows to deletion. **TASK-4126**
tracks accurate Eventbrite diagnostics together with reference-preserving
handling of this newly reachable reconciliation path.

The API's live/public organizer listing cannot distinguish a cancellation
from private, unavailable or otherwise omitted inventory. Neither a missing
ID nor a 403 is used as cancellation evidence in this audit.

## Refresh verification

`verify_source_refresh.py` performs two fresh organizer API reads, actual
Eventbrite parsing and physical-venue routing, with PostgreSQL explicitly
read-only and write fallbacks rejected. It records the original cohort before
and after, verifies repeatable routing, and exercises reconciliation guards
with a delete spy. `refresh-verification.json` contains its sanitized output.

This verifies live source routing and the current no-delete decision, not a
production persistence run. There was no source-confirmed mutation to replay.
It does not prove future availability or guarantee that future source changes
will preserve the same routing. A published return to Oak Street must be
handled through each event's current venue identity, not a permanent Walrus
mapping.

The existing processor, SQL reconciliation and Eventbrite organizer tests
passed: 78 tests covering routing, attribution, deletion caps and fetch/error
guards. Reproduce the live read-only check from `apps/scraper`:

```sh
PYTHONPATH=src:. .venv/bin/python3 docs/audits/attic-unconfirmed/verify_source_refresh.py --output /tmp/attic-refresh.json
```

The 16 event statuses remain unconfirmed. A later disposition requires new
event-specific evidence; this task does not certify these listings as valid.
