-- TASK-3042: Cut the 817 per-venue ticketmaster_comedy nightly scrapers over to
-- the batched ticketmaster_national scraper, to fix the nightly pipeline blowing
-- past the 120-min GHA timeout (root cause: 1360 clubs / max_concurrent_clubs=5,
-- with 817 of them each making a per-venue Ticketmaster Discovery API call behind
-- a shared 5 req/sec limit -> ~3.8h run).
--
-- ticketmaster_national makes ~18 windowed national Discovery API calls
-- (classificationName=Comedy, US, 10-day windows over 180d), groups events by
-- venue, and upserts a club per venue. A read-only validation fetch (TASK-3042)
-- returned 10,615 comedy events across 1,003 venues and covered 784 of the 817
-- per-venue venues; 780 of those matched the existing club name exactly.
--
-- This migration:
--   1. Enables the ticketmaster_national source target (was disabled / "not
--      nightly") so scrape_all_clubs runs it via get_all_source_targets().
--   2. Disables the 780 per-venue ticketmaster_comedy sources that national
--      covers AND whose existing club name exactly matches the national venue
--      name -- national re-uses the existing club via ON CONFLICT (name), so no
--      duplicate clubs and no coverage loss.
--   3. KEEPS enabled (on per-venue) the 37 edge cases listed below = 33 venues
--      national does not surface (beyond the 180d horizon / not classified
--      Comedy nationally / no upcoming comedy) + 4 whose club name differs from
--      the national venue name (keeping their enabled tm_id source makes
--      national's source-insert guard skip them, preventing a duplicate club).
--
-- Idempotent: re-running re-applies the same enabled flags. The keep-list is the
-- source of truth -- any ticketmaster_comedy source whose ticketmaster_id is NOT
-- in the keep-list is disabled.

-- 1. Enable the batched national source target.
UPDATE scraping_sources
   SET enabled = TRUE, updated_at = NOW()
 WHERE scraper_key = 'ticketmaster_national'
   AND source_target_id IS NOT NULL;

-- 2+3. Disable every enabled per-venue ticketmaster_comedy source EXCEPT the 37
--      edge cases national cannot safely replace.
UPDATE scraping_sources
   SET enabled = FALSE, updated_at = NOW()
 WHERE scraper_key = 'ticketmaster_comedy'
   AND enabled = TRUE
   AND ticketmaster_id IS NOT NULL
   AND ticketmaster_id NOT IN (
        'KovZ917ASlK',
        'KovZ917AVf2',
        'KovZ917AYlh',
        'KovZ917Am4e',
        'KovZ917Atn3',
        'KovZpZA17ItA',
        'KovZpZA1EanA',
        'KovZpZA1IFeA',
        'KovZpZA6takA',
        'KovZpZAE7v6A',
        'KovZpZAEAAlA',
        'KovZpZAEe7IA',
        'KovZpZAF76IA',
        'KovZpZAF7dtA',
        'KovZpZAFAtlA',
        'KovZpZAJJEaA',
        'KovZpZAJtF6A',
        'KovZpZAaJ17A',
        'KovZpZAantEA',
        'KovZpZAdIe1A',
        'KovZpa2MCe',
        'KovZpa61pe',
        'KovZpaK80e',
        'KovZpakiGe',
        'KovZpapY1e',
        'Z6r9jZAkFe',
        'Z6r9jZd1ee',
        'Z6r9jZk7Fe',
        'Z7r9jZa7D2',
        'Z7r9jZa7ef',
        'Z7r9jZa7p8',
        'Z7r9jZadaD',
        'Z7r9jZak1X',
        'ZFr9jZ71Fe',
        'ZFr9jZ7vAA',
        'Zkr9jZddeh',
        'rZ7HnEZ173A8A'
   );
