# Public behavior and ingestion retention

Production GET /api/v1/clubs/855 returns200 with the correct Laugh Tonight name
and HTTPS website, empty street/ZIP, null coordinates and a placeholder image.
It no longer represents Dorrian's or The Laugh Tour. Direct hidden club detail
remains addressable by design; this repair does not claim the endpoint returns404.
GET /api/v1/shows/4340528 returns404 Show not found after the club is hidden.
The underlying show/ticket/lineup records are still present, as fingerprinted.

Executed actual ClubQueries.UPSERT_CLUB_BY_SEATENGINE_VENUE in a rollback-only
production transaction using the current live venue424 response (empty address,
ZIP,city/state). All corrected club fields survived; source294 stayed disabled,
owned by855, with SeatEngine424. Migration replay was a no-op. Executing actual
ClubQueries.GET_ALL_CLUBS excluded855 from scheduled ingestion. Verified the
Prisma ledger has a finished, non-rolled-back entry. No new show scrape was needed:
the live feed is empty and its source is intentionally paused.

A second rollback-only upsert with hypothetical Jersey City postal data exposed
a narrower residual risk: blank city/state/ZIP can be refilled even on a stamped
source. It did NOT restore visibility, source enabled, street, coordinates or
Google place identity. No hypothetical changes were committed. This is recorded
in TASK-4109 context745; do not claim the generic upsert protects all unknown fields
against every future changed upstream payload.

TASK-4109 now includes criterion13420 for Laugh Tonight routing, three historical
assignments, cancellation/timezone review, and keeping the source paused until
physical destinations are verified. Context744 carries exact source IDs and
location evidence. This deduplicates the prevention work rather than adding a
second organizer-routing task. An upstream talent named Funny Phat Fridays is
already a hidden blocked comedian1519868 (not a comic) and absent from this stored
show's lineup; no duplicate false-performer cleanup task is needed. Fab Monroe's
home_club link remains untouched pending review of performer geography.

## Validation

12 focused tests passed (0.23s):

```sh
cd apps/scraper
PYTHONPATH=src:. .venv/bin/python3 -m pytest   tests/core/entities/test_club_handler.py::TestSeatEngineUpsertRespectsDispositionMetadata   tests/scrapers/implementations/api/seatengine_national/test_seatengine_national_scraper.py -q
```

The full web gate had2408 passing and3 failing savedShow.test.tsx cases. Required
Tusk precheck replayed the exact command on unchanged HEAD three times: all failed,
not flaky, no origin/main divergence. web-baseline.json records that verdict;
TASK-3983 already tracks the unrelated failures. Commits used the skill's
path-limited fallback. All SQL production-shape validation is in validation.json;
post-apply reference and ingestion/public assertions are in verification.json.
