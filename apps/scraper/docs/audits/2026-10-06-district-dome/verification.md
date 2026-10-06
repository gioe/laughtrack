# Verification — TASK-4117

## Production data and discovery replay

The exact production after-state matched the reviewed expected state. Through the
actual `ClubHandler.upsert_for_seatengine_venue` entry point, the freshly fetched
native venue 534 was replayed twice in a rollback-only transaction: once with
ZIP 85050 and once with stale ZIP 85054. Both returned existing club 554 and
preserved the entire business snapshot, including hidden visibility, corrected
postal identity, disabled source 87, native ID/URL, and disposition marker.
`ClubQueries.GET_ALL_CLUBS` excluded 554. Separate Carry On club 600/source 336
were unchanged. The transaction rolled back. Counts and hashes are in
`repair-receipt.json`.

## Public endpoint checks on 2026-10-06

- `/api/v1/shows/522028`: HTTP 200 before quarantine, HTTP 404 afterward.
- `/api/v1/shows?zip=85050&distance=1&from=2027-06-04&to=2027-06-06`:
  HTTP 200, total 0, empty data after quarantine.
- `/api/v1/clubs/search?club=District%20Dome&includeEmpty=true`:
  HTTP 200, total 0, empty data after quarantine.
- Pagination of `/api/v1/clubs?limit=100&offset=200` uncovered a separate escape
  in the same required discovery behavior: its `getClubs` query required active
  status and future shows but omitted visibility. It still returned club 554.

This task adds `visible: true` to the shared mobile-list/home-carousel query and
extends both ordinary-list and image-required query tests. This keeps historical
inventory and venue operating status intact while honoring the existing hidden
venue policy. The list endpoint needs the web deployment from this task; verify
fresh pagination after deployment and record the outcome against criterion 13419.
That production check is explicitly deferred until merge/deployment, not claimed
as already passed by this document.

## Tests

- 16 PostgreSQL repair/discovery tests passed with temporary tables on local
  PostgreSQL: `tests/scripts/test_quarantine_district_dome.py` and
  `tests/core/entities/club/test_seatengine_quarantine.py`.
- 23 Vitest tests passed: `lib/data/home/getClubs.test.ts` and
  `app/api/v1/clubs/route.test.ts`.
- The full web gate failed existing Canadian permanent-time runtime tests. Exact
  clean-base replay failed 3/3, with `pre_existing=true`,
  `diverged_from_default=false`, and `flaky_suspect=false`. Required recovery used
  path-restricted Git commits; no unrelated timezone code was changed. The agent
  email was unavailable, so fallback commits omit a guessed coauthor trailer.
