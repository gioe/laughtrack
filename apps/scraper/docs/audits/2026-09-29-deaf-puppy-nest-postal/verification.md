# Public nearby discovery and retention

Before repair, production searches returned data=[]/total0 for both targets.
After repair the identical ZIP/radius/name queries return their respective venue:

- /api/v1/clubs/search?zip=95336&distance=5&club=Deaf%20Puppy&size=50&includeEmpty=true → club551
- /api/v1/clubs/search?zip=43202&distance=5&club=Nest&size=50&includeEmpty=true → club8713

Both records remain visible,active,countryUS with62 and36 upcoming shows. Public
club detail endpoints return95336 and43202 with unchanged street and business
coordinates. These are actual production responses, preserved in verification.json;
nearby-before files preserve the excluded baseline. This verifies membership in
US nearby search, not guaranteed placement in every image/lineup/ranking-limited rail.
Nest has_image=false is unchanged and can still exclude it from image-only rails.

All direct FK counts and row fingerprints, source config and non-ZIP club fields
are unchanged.315 historical shows,322 tickets and all saved/lineup/click references
are preserved. Missing-only production-shaped validation also proved2760 already
populated ZIP values and2884 other club records unchanged; see validation.json.

In a rollback-only production transaction the actual SeatEngine national upsert
for531 was supplied an incorrect incoming ZIP00000: Deaf Puppy's95336 survived.
Both clubs remain in the actual GET_ALL_CLUBS scheduler selection. Migration replay
is a no-op, and the Prisma ledger is finished/non-rolled-back. VBO event ingestion
does not write venue postal fields; its existing pipeline smoke tests passed.
No source change or speculative postal parser was needed, and no follow-up task
is necessary for these two resolved evidence gaps.

Focused checks passed:
-125 scraper tests: test_zip_preservation.py, seatengine_national/test_seatengine_national_scraper.py,
  vbo_tickets/test_pipeline_smoke.py (worktree src explicitly on PYTHONPATH).
-29 web tests: QueryHelper.getZipCodeClause.test.ts, clubLocationFiltering.test.ts,
  getClubsByZip.test.ts and getShowsNearZip.test.ts.

Full web gate initially had2407 passing and4 failing cases: three savedShow.test.tsx
failures plus one AdminClubManager thumbnail case. Required unchanged-HEAD precheck
ran the exact suite three times:2408 passing/three savedShow failures every run,
no origin divergence, verdict pre_existing. The thumbnail failure did not recur
in those three runs. TASK-3983 tracks the persistent saved-show failures; no changes
were made to unrelated UI tests. Used the documented path-limited commit fallback.
