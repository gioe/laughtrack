# TASK-2094 Null Show Attribution Audit

Date: 2026-05-09

## Finding

The 3,699 future shows with `last_scraped_by IS NULL` are legacy rows from
before `shows.last_scraped_by` existed, not evidence of a current writer
regression.

Evidence from production:

- Future NULL-attributed rows: 3,699
- Newest affected `last_scraped_date`: 2026-05-08 15:25:09 UTC
- Future NULL-attributed rows with `last_scraped_date >= 2026-05-09 12:00:00 UTC`: 0
- Rows attributable from a single enabled `scraping_sources` row on the club: 3,315
- Rows from old Eventbrite organizer venues with no current source row but
  unambiguous Eventbrite URLs: 220
- Rows from legacy The Comedy Club On State Madison URLs: 18
- Rows on hidden non-comedy/test/duplicate clubs with no current source row: 146

## Writer Audit

All current scraper show writes flow through attribution-aware persistence:

- `BaseScraper.scrape_with_metrics()` returns `ClubScrapingResult(scraper_key=self.key)`.
- `ScrapingResultProcessor.insert_club_result()` forwards
  `club_result.scraper_key` into `ShowService.insert_shows()`.
- `ShowService.insert_shows()` forwards `scraper_key` into
  `ShowHandler.insert_shows()`.
- `ShowHandler.insert_shows()` stamps every show whose `last_scraped_by` is
  unset before upsert.
- `ShowQueries.BATCH_INSERT_SHOWS` inserts `last_scraped_by` and preserves an
  existing attribution only when the incoming row lacks one.
- The non-club `tour_dates` writer calls `ShowHandler.insert_shows(...,
  scraper_key=self.key)` directly.

The only direct `insert_shows()` callsites found are the processor path above
and `tour_dates`; both provide a scraper key.

## Cleanup

Migration `20260509193500_backfill_future_show_attribution` backfills the
deterministic cases and deletes the remaining hidden/no-source future rows.
The projected future NULL count after applying that migration is 0, which is
below the task threshold of 100.
