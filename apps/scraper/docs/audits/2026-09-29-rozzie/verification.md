# Public and ingestion verification

Production GET https://www.laugh-track.com/api/v1/clubs/10970 and
GET https://www.laugh-track.com/api/v1/shows/3179461 returned HTTP 200 with
the corrected club address. Venue response also contains ZIP 02131 and the
reviewed coordinates. See verification.json; this validates public API data,
not a screenshot or an assertion about every client cache.

## Retention during ingestion

In a rolled-back production transaction, ran the actual
ClubQueries.UPSERT_DISCOVERED_VENUE with the same venue name, old Basile
address, deliberately wrong ZIP 00000, and stale city/state. It retained all
four repaired fields and source 6820 remained enabled/attached to club 10970.
Replaying the migration after that upsert was a no-op. GET_ALL_CLUBS still
selects the active visible club. Confirmed successful Prisma ledger entry.

AnyRoadScraper resolves the existing source plugin, and its transformer sends
locationInfo into Show.room. Event.to_show binds the configured club ID and
does not update club address/ZIP/coordinates. The archived onboarding helper
returns the matching place-ID/name row before any insert; replay cannot
replace its identity. No recurring writer fix is needed for this correction.
Existing image-source identity protection is separately tracked by TASK-4113.

Focused pytest command from apps/scraper:

    PYTHONPATH=src .venv/bin/python3 -m pytest tests/scrapers/implementations/anyroad/test_scraper.py tests/scrapers/implementations/anyroad/test_extractor.py tests/core/entities/club/test_zip_preservation.py -q

Result: 115 passed. Includes real AnyRoad extraction/transformation using the
Rozzie fixture, correct event times, stable club binding and Corinth room text.
Live upstream AnyRoad scrape could not be verified because the local stack
received 403 and lacks the Playwright fallback package. No scrape was run
that writes new production shows. This limitation is independent of the
verified database upsert replay and does not establish a production outage.

Full web gate: 2,408 passed, three failures in savedShow.test.tsx. Required
clean-HEAD precheck ran three times: all failed, flaky_suspect false, no
upstream divergence. This is the already-tracked TASK-3983 baseline failure;
web-baseline.json captures the result. Used path-limited commits under the
Tusk pre-existing failure policy; no unrelated test fixes were attempted.

## Follow-up

Created high-priority TASK-4116 after semantic and heuristic deduplication:
Handle offsite AnyRoad show venues separately from the organizer theater.
Scope is AnyRoad implementation/tests, audited data repair and Prisma migrations.
It covers the four Substation rows, authoritative review, safe routing and
future ingestion. All are preserved by this migration. Do not automatically
restore Basile based on the venue's projected fall 2027 reopening date.
