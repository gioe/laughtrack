-- Add shows.last_scraped_by for scraper attribution.
--
-- TASK-2032's Live Nation orphan-row audit had to reverse-engineer attribution
-- from URL patterns + live API spot-checks because shows recorded last_scraped_date
-- but not which scraper produced the row. Storing the scraper_key directly
-- collapses that audit to a single WHERE clause and unblocks generic
-- orphan-cleanup queries (e.g. "shows whose last_scraped_by no longer maps to
-- an enabled source on the club").
--
-- Backfill is conservative: only URL hosts that map unambiguously to exactly
-- one scraper get attributed. Ambiguous hosts (tixr.com — split into
-- tixr/tixr_public_card by TASK-2044; eventbrite.com — eventbrite vs.
-- eventbrite_national; ticketmaster.com — live_nation vs. ticketmaster_national;
-- services.seatengine.com — seatengine_classic vs. seatengine_v3 vs.
-- seatengine_web vs. seatengine_national vs. seatengine_v3_national) stay NULL
-- and pick up correct attribution on the next nightly run.

ALTER TABLE shows ADD COLUMN last_scraped_by TEXT;

CREATE INDEX shows_last_scraped_by_idx ON shows (last_scraped_by);

UPDATE shows
SET last_scraped_by = 'tour_dates'
WHERE last_scraped_by IS NULL
  AND show_page_url ~* '(?:^|//)(?:www\.)?bandsintown\.com/';

UPDATE shows
SET last_scraped_by = 'etix'
WHERE last_scraped_by IS NULL
  AND show_page_url ~* '(?:^|//)(?:www\.|event\.)?etix\.com/';

UPDATE shows
SET last_scraped_by = 'ticketweb'
WHERE last_scraped_by IS NULL
  AND show_page_url ~* '(?:^|//)(?:www\.)?ticketweb\.com/';
