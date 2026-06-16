-- TASK-2921: Migrate The Rockwell off the venue-specific the_rockwell scraper
-- onto the generic the_events_calendar (Tribe Events) scraper added in TASK-2865.
--
-- The Rockwell (club 150) already exposes the standard Tribe Events REST API at
-- https://therockwell.org/wp-json/tribe/events/v1/events, which the generic
-- the_events_calendar scraper reads directly from scraping_sources.source_url.
-- The the_rockwell scraper + RockwellEvent entity were a near-exact duplicate of
-- the generic Tribe scraper and are deleted in this task; repoint the only row
-- that referenced the old key. platform stays 'tribe_events' (matches the other
-- the_events_calendar venues 8705/8710).

UPDATE scraping_sources
   SET scraper_key = 'the_events_calendar',
       updated_at = now()
 WHERE id = 75
   AND club_id = 150
   AND scraper_key = 'the_rockwell';
