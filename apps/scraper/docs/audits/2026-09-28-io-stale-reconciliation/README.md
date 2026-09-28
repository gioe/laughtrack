# TASK-4063: iO Theater stale-show reconciliation

## Finding

The safety cap is working. The September 28, 2026 snapshot contains **42 future stored rows whose timestamps are absent from the live feed**, exceeding the unchanged default cap of 10. The current extractor preserves all 1,519 source performances. The evidence supports accumulated schedule changes and delisted occurrences, rather than a demonstrated timestamp parser failure. One candidate has conflicting source evidence and must be preserved pending resolution.

No production scrape, deletion, configuration change, or cap override was performed. This snapshot is investigation evidence, not a deletion manifest approved for execution.

## Comparison

Source: <https://crowdwork.com/api/v2/iotheater/shows>, club 182, scraping source 45, timezone America/Chicago. The fixed comparison cutoff is `2026-09-28T00:44:50.541695+00:00`; exact retrieval timestamps and the read-only SQL are in `manifest.json`.

| Measure | Count |
| --- | ---: |
| Source event listings | 78 |
| Raw performances, including past dates | 1,519 |
| Future source performances | 1,255 |
| Stored future rows | 946 |
| Exact stored URL/UTC-time matches | 904 |
| Unmatched stored rows | 42 |
| Unmatched rows at a timestamp occupied by another feed event | 0 |
| Future timestamps shared by distinct source URLs | 282 |

All stored rows have an empty room. All 42 candidates were last produced by Crowdwork. The actual reconciliation query uses source ownership and a pre-upsert freshness cutoff; the read-only comparison predicts which existing rows a successful scrape would fail to refresh. It does not run that mutation pipeline.

The saved September 24 feed contains 1,494 performances, matching the original log. Six current candidates were present in that older feed, and 36 were already absent. The original log reports 37 candidates, but no complete historical DB snapshot is retained, so this audit does not claim to reconstruct those exact 37 IDs.

## Classification of every candidate

`candidates.jsonl` contains all 42 IDs, original URL, UTC/local timestamp, last scrape time, classification, source evidence, and replacement identity where applicable. `pages.jsonl` retains sanitized public-page date links and structured event fields for all 13 affected series.

| Classification | Rows | Evidence and limits |
| --- | ---: | --- |
| Series absent; page only advertises past performance | 19 | The Orbit is absent from both feeds; its page shows September 9, sales closed, and no future date links. This establishes delisting, not an explicit cancellation reason. |
| Individual occurrence absent | 11 | Cage Match (1), ComedySportz (1), Harolds After Dark (2), Sketch Playlist (1), Blueprint (1), iO House Team Night (2), Improvised Romantasy (1), The Tension is Laughable (1), People Being Funny (1). Series remain listed, but each candidate date is absent from the feed and page date links. Several cluster around Halloween/November 5–7; no cause is inferred from that clustering. |
| Same local date, time moved 30 minutes earlier | 6 | People Being Funny is listed at 21:30 instead of stored 22:00. Five replacement URL/time identities exist in storage; the October occurrence is lost to a separate collision. |
| Monthly recurrence changed | 4 | Mystery Movie Club January–April lists first Thursday at 19:00 instead of the stored third Thursday. All four replacements are stored. Compare calendar dates in America/Chicago across DST, not fixed UTC durations. |
| Date moved two days later | 1 | This Year in Music lists December 11 at 19:00 instead of December 9; replacement row 1044696 exists. |
| Conflicting future-date evidence | 1 | Flex Improv row 480692: absent from feed and page date selector, but description explicitly lists November 5 at 19:30, matching the stored occurrence. Preserve while this conflict remains unresolved. |

Public pages sometimes expose dates beyond the feed's horizon, and several date selectors show only a limited set. Absence from a page selector alone is not proof of cancellation; classifications above combine the feed with page evidence, and cleanup requires fresh verification.

## Separate source-identity defect

Crowdwork's event conversion sets an empty room. The database key is venue/date/room, so distinct event URLs sharing a timestamp collide. Deduplication keeps the first event within each 100-show batch; a later batch can overwrite that row with another title/URL. This loses valid performances, but does **not** explain the 42 stale timestamps, which are absent from every current feed event.

Concrete example: source events People Being Funny and Paranormal Laughtivity both list October 2 at 21:30 Chicago time (`2026-10-03T02:30:00Z`). Stored row 480923 contains Paranormal Laughtivity. People Being Funny's valid occurrence is absent, while its obsolete 22:00 row 3736581 remains. Cleanup must not silently remove that old row without addressing or explicitly holding the missing replacement.

## Reproduce and verify

From `apps/scraper`, using this worktree's source:

```bash
PYTHONPATH=src:. .venv/bin/python3 docs/audits/2026-09-28-io-stale-reconciliation/replay.py
PYTHONPATH=src:. .venv/bin/python3 -m pytest \
  tests/utilities/domain/scraper/test_result_processor.py::TestStaleFutureShowReconciliation::test_cap_exceeded_skips_delete \
  tests/core/entities/show/test_handler_stale_reconciliation.py \
  tests/scrapers/implementations/api/test_crowdwork_scraper.py -q
```

The replay checks the captured evidence hashes, actual extractor/date parser, every candidate ID, all 11 source-listed replacements and their stored coverage. The focused test run passed 20 tests, including refusal to delete above the cap and source-scoped reconciliation predicates. The replay has no database/network calls.

`collision_repro.py` separately reproduces the current distinct-event collapse with the actual persistence deduplication helper. Its desired-behavior assertion is expected to fail until the identity follow-up is implemented; it is an audit reproduction, not a passing test-suite addition.

## Follow-up work

- **TASK-4105 — Reconcile verified stale iO Theater performances with an evidence-locked cleanup.** Revalidate the exact IDs; preserve the conflicting Flex Improv row and hold any missing valid replacement; prepare guarded transactional repair and rollback evidence. Verify before/after IDs and retained references. Keep the runtime cap unchanged.
- **TASK-4106 — Preserve simultaneous Crowdwork performances with distinct event URLs.** Add persistence coverage for distinct URL/same timestamp events, both input orders and batch boundaries, plus same-event duplicate handling. Preserve source identity without fabricating physical rooms. Verify the live October People Being Funny/Paranormal Laughtivity pair.

The tasks are independently actionable: cleanup can review safe candidates while explicitly holding unresolved replacements. Related TASK-4081 covers Annoyance Theatre identity, not Crowdwork; its implementation may inform a shared design.

## Evidence handling

`feed.jsonl` and `previous-feed.jsonl` retain only public event IDs, names, URLs, timezones and dates. `stored.jsonl` retains show metadata only. Public-page checks used the scraper's Playwright browser after plain curl returned 403; that response was not treated as a missing event. Raw HTML, form tokens, cookies, source configuration secrets and user data are excluded from committed artifacts. HTML hashes identify the locally inspected pages; sanitized projections are retained for review.
