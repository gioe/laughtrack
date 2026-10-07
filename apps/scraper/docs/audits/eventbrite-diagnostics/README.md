# Eventbrite diagnostics and Attic inventory preservation

TASK-4126 separates HTTP/page success accounting from authorization to delete
missing inventory. An Eventbrite live/public feed excludes private, unpublished,
and otherwise unavailable events. A complete successful response does not prove
that an omitted performance was cancelled or may safely lose its user history.

## Failure reproduced

The pre-change read-only refresh on 2026-10-07 returned 45 source events on one
HTTP 200 page, with 44 routed to The Walrus (29044) and one to Attic (575).
Diagnostics incorrectly reported zero successful and zero failed fetches. All 16
original unresolved Attic rows remained; 10 were future inventory, exactly the
configured deletion cap of 10. Fixing counters alone would therefore remove the
accidental protection supplied by the zero-success cleanup gate.

The existing `../attic-unconfirmed/verify_source_refresh.py` audit fetches pages
separately and mocks `fetch_all_events` during routing. It established the
baseline but does not prove the corrected accounting through the real organizer
pipeline. This audit's verifier passes the actual `EventbriteClient` into
`_scrape_organizer_async`, observing page responses without replacing them.

## Reproduce safely

From the task worktree's `apps/scraper` directory:

```sh
PYTHONPATH=src:. .venv/bin/python3 docs/audits/eventbrite-diagnostics/verify_source_refresh.py --output /private/tmp/task4126-after.json
```

The verifier performs two live organizer refreshes and existing-venue lookups.
The PostgreSQL connection is read only; non-SELECT handler operations, venue
upsert fallbacks, and secondary connections are refused. Show persistence never
runs. The script fails if source routing drops a fetched event, changes a source
instant, fails to complete pagination, emits scrape errors, or does not account
for every successful page in bound diagnostics.

Each pass also exercises the real stale-inventory cleanup entry point against
in-memory persistence spies, using positive successful-fetch counters and
candidate counts at and below the configured cap. Both ordinary club and
synthetic organizer results must make zero persistence calls. Synthetic results
carry a production-company identifier so a missing policy guard cannot pass
merely because organizer configuration is incomplete.

Before and after the refreshes, a single SQL statement snapshots every column of
the 16 original show rows and their seven dependent tables: tickets, lineups,
tags, saved shows, sent notifications, discovery snapshots, and purchase clicks.
READ COMMITTED gives each observation a fresh database snapshot; concurrent net
changes are detectable instead of being hidden by a repeatable-read snapshot.
Only show rows and child-table counts/keyed fingerprints are exported. Private
child records stay in memory, and the ephemeral HMAC key is discarded, preventing
offline guesses against low-entropy private values. Fingerprints are comparable
only within one report. A changed snapshot causes a nonzero exit after writing
the report; it must be investigated rather than attributed automatically to this
read-only verifier.

## Interpretation limits

Absence remains `absent_unconfirmed`; this audit authorizes no cancellations,
hard deletions, permanent Attic-to-Walrus remapping, or production writes. The
read-only check proves client accounting and routing, not persistence
idempotence. A change reversed between observations cannot be detected by net
snapshots. Inventory may legitimately change between the two source refreshes;
the report exposes that comparison separately.

## Verified result

The 2026-10-07 refresh passed twice: each fetched one HTTP 200 page containing
45 events, with `fetches_ok=1`, `fetches_failed=0`, and no scrape errors. Routing
was identical on both passes (44 Walrus, one Attic). All 16 unresolved shows and
434 linked records (16 tickets, 59 tags, 359 purchase clicks) remained exact.
Both cleanup modes made zero persistence calls for candidate counts 1, 9 and 10
even though their diagnostic cleanliness gate was true. See `live-receipt.json`.

All 149 focused Eventbrite client/scraper and result-processor tests passed.
The full scraper gate failed during collection because the environment lacks
`tzdata`; three unchanged-HEAD precheck runs reproduced it with no upstream
divergence. Commits used the documented path-limited fallback. Agent attribution
trailers were omitted because no executing-agent email was available.
