-- TASK-2823: Re-adopt Comedy Key West after the former Punchup /shows page
-- started returning a SeatEngine "Page Not Found" document.
--
-- Live inspection on 2026-06-12 found comedykeywest.com is now SeatEngine
-- Classic:
--   * https://www.comedykeywest.com/shows returns 404 content.
--   * https://www.comedykeywest.com loads cdn.seatengine.com assets.
--   * /events and /calendar expose the active ticketing/calendar pages.
--
-- The generic seatengine_classic scraper parses /events directly and merges
-- sibling /calendar JSON-LD events. A local probe transformed 81 upcoming
-- show instances from https://www.comedykeywest.com/events.

UPDATE clubs
   SET website = 'https://www.comedykeywest.com'
 WHERE id = 98;

UPDATE scraping_sources
   SET platform = 'seatengine',
       scraper_key = 'seatengine_classic',
       source_url = 'https://www.comedykeywest.com/events',
       seatengine_id = NULL,
       eventbrite_id = NULL,
       ticketmaster_id = NULL,
       wix_event_id = NULL,
       ovationtix_id = NULL,
       squadup_id = NULL,
       seatengine_v3_id = NULL,
       metadata = '{}'::jsonb,
       updated_at = now()
 WHERE id = 109
   AND club_id = 98;
