# Activation and live verification — October 5, 2026

The guarded activation dry run passed and rolled back. Apply then committed source
617's replacement, production company **48**, and these physical destinations:

| Club | Venue | State | Current performances |
| --- | --- | --- | ---: |
| 90831 | Big Shots Restaurant & Lounge | NJ | 1 |
| 90832 | Mauch Chunk Opera House | PA | 0 |
| 90833 | Arcadia Clubhouse | SC | 0 |
| 90834 | Newtown Theatre | PA | 9 |
| 90835 | Dreamers Restaurant | SC | 2 |
| 90836 | Wonders Theatre | SC | 13 |
| 90837 | Bloomsburg Theatre Ensemble | PA | 0 |

All seven new clubs are source-less physical records, with seven producer/venue
relationships. Source 617 retains its owner, priority, and enabled status; its
previous configuration is preserved in its activation marker. Organizer 327 and
unrelated Arcadia bar 76800 were unchanged. Both source targets, 56 existing shows,
56 tickets, 42 lineup rows, 80 tags, and 1,161 historical clicks matched their full
before-images after activation. The private durable recovery files are
`/private/tmp/task4112-recovery.json` and its `.after.json` companion.

Two actual scraper runs used worktree-local imports:

```sh
PYTHONPATH=src:. make scrape-club CLUB='The Comedy Shoppe'
```

The first run at 20:03 EDT and second at 20:04 EDT each returned 25 valid comedy
performances. The second run key was `scraper:2026-10-05T20:04:21.957076`. All 27
native events were accounted for: 25 retained plus the two explicitly excluded
Day Players concerts. No missing-location or pagination errors were ignored.
`persisted-performances.json` records each retained native ID, exact ticket URL,
aware timestamp, physical club, and producer provenance.

A read-only comparison after each run checked all 25 native dates against the
America/New_York instant and all destination IDs against reviewed routes. Club327
still has zero upcoming shows. The second run retained the exact same 25 show IDs,
25 tickets, 37 lineup rows, and 50 tags. All business fields and relationship IDs
were unchanged (routine updated_at/last_scraped_date fields were excluded from
repeat comparison). All 56 historical/preserved shows and every one of their seven
relationship tables remained exactly unchanged, including all 1,161 clicks.
Source617 and both source targets also matched activation after-images exactly.
The per-run private snapshots are `/private/tmp/task4112-live1-state.json` and
`/private/tmp/task4112-live2-state.json`; never commit them.

## Test evidence

The pre-fix regression reproduced 20 extracted events where the captured complete
calendar has 24. The final combined suite passed **111 tests**, including the
original 24-event fixture at its original clock, the current 24-event HTML fixture,
27-event API pagination, concert exclusions, malformed/foreign query handling,
conflicting identities, unavailable or changed destinations, source-less lookup,
reconciliation guards, source activation drift/duplicate checks, and real local
PostgreSQL repeated persistence with relationship preservation. Existing PunchUp,
Side Splitters, and ShowSlinger regression tests remain green.

```sh
TEST_DATABASE_URL=postgresql:///postgres PYTHONPATH=src:. .venv/bin/python3 -m pytest \
  tests/scripts/test_activate_comedy_shoppe_punchup.py \
  tests/scrapers/implementations/venues/the_comedy_shoppe \
  tests/core/clients/punchup \
  tests/scrapers/implementations/venues/side_splitters -q
```

The full commit gate could not collect because the shared virtualenv lacks tzdata.
Clean-HEAD precheck reproduced that same error on all three runs, with no upstream
divergence or flaky result. The focused suite and live operations passed; this is
not a claim that the full repository suite passed.

## Recovery boundary

Before reverting source activation, lock the same tables and compare source617
and all affected identities against the private after-image; refuse any unexplained
drift. Restore only the changed source fields from the saved previous source row,
allowing its update timestamp trigger. The correctly routed new performances and
physical identities should remain intact when merely reverting source ingestion.
Do not delete new venues or producer48 after ingestion: they now have live show,
ticket, lineup and tag references. Any rollback of those performances requires a
new reviewed dependent-aware disposition and private snapshot; the activation
backup alone predates the two live scrapes. Private per-run snapshots preserve the
post-ingestion rows for that review. Existing historical rows were never changed.
