-- Onboard Mesquite St. Comedy Club (club 837) to the new TicketLeap scraper.
--
-- The TicketLeap scraper was verified to produce 7 live shows from the 'funny'
-- org listing (https://events.ticketleap.com/events/funny). Club metadata
-- (address, timezone, scraping_url, website) was already set by migration
-- 20260416180721_update_mesquite_st_comedy_ticketleap_metadata.
--
-- This migration:
--   * switches scraper from the stale 'seatengine' key to 'ticketleap'
--   * clears seatengine_id (the venue has moved off SeatEngine)
--   * unhides the club so shows appear on the site
UPDATE clubs
SET scraper       = 'ticketleap',
    seatengine_id = NULL,
    visible       = TRUE
WHERE id = 837;
