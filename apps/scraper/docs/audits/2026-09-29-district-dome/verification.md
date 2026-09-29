# Public location and ingestion retention

After applying the migration, production club 554 and show 522028 API responses
returned the reviewed 21001 N Tatum Blvd, Phoenix, AZ 85050 address. The club
response also returned zipCode 85050 and the unchanged business coordinates.
See verification.json for the responses and verified Prisma ledger entry.

A production transaction executed the actual
ClubQueries.UPSERT_CLUB_BY_SEATENGINE_VENUE with District Dome, venue534,
its original address and stale ZIP85054. The reviewed address and ZIP survived,
and source87 retained its owner, enabled flag and SeatEngine ID. Migration
replay after the upsert was a no-op; scheduler selection retained club554.
The transaction was rolled back. This tests ingestion persistence without
writing a new scrape or claiming the event's physical location is valid.

The live upstream API was separately fetched through the scraper HTTP client:
venue534 identifies District Dome, its own website and America/Phoenix; the
single current feed result joins exactly to stored show522028 by source ID and
UTC timestamp. The ticket detail contains 11 inventories. That source evidence
is not a reason to overwrite physical venue identity from event prose.

Focused tests: 106 passed across test_zip_preservation.py and
seatengine_national/test_seatengine_national_scraper.py, with worktree src
explicitly placed on PYTHONPATH to avoid the primary venv's editable install.

Full web gate: 2,408 passed and three savedShow.test.tsx failures. Required
unchanged-HEAD precheck repeated the same command three times; web-baseline.json
records the verdict. TASK-3983 already tracks these unrelated failures. Used
the documented path-limited commit fallback; did not modify unrelated tests.

All direct club/show FK counts and fingerprints are unchanged, including one
show, 11 tickets, three tags, 138 scraper-run links and 23 purchase-click rows.
Source configuration and all club fields except address and zip_code match.

TASK-4117 separately tracks the contaminated Carry On description, non-comedy
programming review, guarded suppression and source re-enable protection. It is
high priority and deduplicated against TASK-4109, whose organizer-routing repair
covers different venues. This task does not claim District Dome is now clean
comedy inventory; it resolves and preserves only its verified postal address.
