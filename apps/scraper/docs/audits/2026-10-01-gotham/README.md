# TASK-4087: Gotham explicit description billing

Verified October 1, 2026 using a fresh 433-item feed capture and a read-only
GothamComedyClubScraper.scrape_with_result run through the normal feed pagination,
Showclix ticket enrichment, transformer and Show validation. The scrape returned
110 upcoming performances, three with explicit textual billing (six links).

- 4400553, Laugh for Sight: Mark Normand, Aaron Berg, Cory Kahaney, Shaun Eli.
- 6370626, Mixtape Comedy Show: Royale Watkins.
- 5645376, Mixtape Comedy Show (As Part of the NYCF): Royale Watkins.

Only these three venue/date/source-URL matches were refreshed through the normal
ShowService. Persistence added six memberships and one explicitly billed person
through the standard comedian handler. No title-derived identities were created.
The existing cross-batch reconciliation retained Laugh for Sight's blank room
rather than duplicating it under the feed model's Main Room default.

All 609 show IDs, 609 ticket IDs, dates, rooms, prices and ticket availability
remained unchanged. The 606 unmatched records retained their original lineups,
URLs and scrape timestamps. No other performances were inserted or deleted.

The recurring fix preserves source descriptions and reads only an exact Featuring
heading with contiguous name entries, or an explicit leading Hosted by clause.
Section boundaries end billing; alumni, biography/TV credits and music references
are not mined for names. Normal lineup validation and placeholder suppression
still apply. Missing or unannounced descriptions produce empty lineups.

All 58 Gotham tests passed, including both named task regression tests. The full
scraper gate passed in 77.8 seconds. Captured TASK-4055 descriptions supply the
historical regression cases; source-billing.json retains the fresh three records.
Poster-only extraction remains the separate TASK-4088 scope.
