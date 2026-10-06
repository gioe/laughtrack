# TASK-4116 execution and verification

Applied October 6, 2026 after a rolled-back dry run. The exact reviewed manifest
is `reviewed-plan.json`; it pins both physical venues, source 6820, and all 146
show before-images. No new physical club or scraping source was created.

## Production outcome

| Inventory | Before | After |
| --- | ---: | ---: |
| Rozzie Square Theater 10970 | 144 | 142 |
| The Substation 61212 | 2 | 4 |
| Total shows | 146 | 146 |
| Tickets | 146 | 146 |
| Tagged shows | 256 | 256 |
| Ticket click records | 1,973 | 1,973 |

Every child row is byte-for-byte equal in the JSON snapshots; lineups, saved
shows, notification links, and discovery snapshots were empty in this cohort
and remain empty. All forty blank-room organizer shows remain unchanged.
Source 12257 and its two existing Substation shows are unchanged. Both physical
clubs remain visible, with their original addresses and timezones.

The guarded transaction moved 3179506 and 3558318 to club 61212; corrected only
the room of 3179545 at club 10970; and left historical 3179544 exactly unchanged.
The three changed shows now reference real producer 50 (The Rozzie Square
Theater), including scraper organizer ownership. The source remains on club
10970 and its existing plugin metadata is retained. Producer-to-venue links
cover both physical sites. A second dry run returned `already_applied: true`.

The apply entry point was
`scripts/core/repair_anyroad_offsite_venues_2026_10_06.py`; after execution it was
archived to `scripts/archive/repair_anyroad_offsite_venues_2026_10_06.py` under
convention 325. Tests import the archived version.

## Public and ingestion checks

Fresh public API GETs returned HTTP 200 for upcoming 3179545, moved 3179506, and
held 3179544. `public-verification.json` stores only their public projections.
The first cached request for 3179545 still showed the old room; a fresh query
returned the corrected room with `x-vercel-cache: MISS`, `age: 0`. The API keeps
its existing `max-age=60` policy. The upcoming show remains November 5 at 8pm
America/New_York, with its original $11 ticket and booking URL.

A read-only live `AnyRoadScraper.scrape_with_result()` using the applied source
configuration and scraper HTTP stack fetched 37 distinct experiences and
produced 130 occurrences, all at the home theater as the current feed advertises.
There were no routing errors, failed fetches, or bot-block flags; reconciliation
eligibility was clean. Its November 5 Level 1B candidate exactly matches the
repaired club, room, instant, producer, and ticket price. See `live-replay.json`.
The replay did not persist inventory. Future offsite routing and repeated
persistence were exercised against local PostgreSQL rather than inventing an
offsite occurrence absent from the current feed.

## Regression checks and limitation

- 104 focused tests passed: AnyRoad extraction/routing, physical lookup,
  result processing, and stale reconciliation. PostgreSQL repeat-refresh tests
  use batch sizes 1 and 100 and preserve show, ticket, saved-show and click IDs.
- Ten additional real PostgreSQL repair tests passed, including after archiving:
  exact moves/hold, native and room collisions, before-image drift, backup failure
  before writes, repeat no-op, exact rollback, and new-producer-reference refusal.
- Black, pyflakes and diff whitespace checks passed for the implementation.
- The full scraper gate cannot collect because the shared environment lacks
  `tzdata`. Tusk precheck reproduced this on unchanged HEAD three times, without
  flakiness or upstream divergence. The documented path-limited commit fallback
  was used; the unrelated dependency was not changed.

## Recovery

Private recovery snapshots (mode 0600) are retained at
`/private/tmp/task4116-production-before.json` and its `.after.json` companion.
They include private relationships and are deliberately excluded from Git.
The full after-image is required for rollback. From `apps/scraper`, use:

```sh
PYTHONPATH=src:. .venv/bin/python3 scripts/archive/repair_anyroad_offsite_venues_2026_10_06.py \
  --rollback /private/tmp/task4116-production-before.json.after.json
```

Rollback checks the complete affected after-state, including new references to
the producer, before restoring the original source configuration, show fields,
counts and producer links. Any subsequent scrape or related-row drift requires
fresh review; do not bypass the guard. Rollback was tested locally and was not
performed against the successfully repaired production data.
