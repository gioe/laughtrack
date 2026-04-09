-- TASK-1108: Fix AC Jokes (id=412) — repoint from dead SeatEngine to live Wix site.
--
-- Investigation findings:
--   - Original SeatEngine subdomain (4bc8f310-...seatengine.com) is defunct:
--     API returns 404, events page shows 0 events
--   - Real website is acjokes.com (Wix), which has 20+ upcoming shows across
--     4 venues (Resorts Casino, The Hook at Caesars, The Cove Brigantine,
--     Hi Point Pub Absecon)
--   - Wix Events calendar widget shows shows from Apr 10 through May 9+
--   - Club was missing city/state metadata
--
-- Action: update website, scraping_url, city, state. Scraper type change
-- to wix_events will be handled in onboarding task.

BEGIN;

UPDATE clubs
SET website     = 'https://www.acjokes.com',
    scraping_url = 'https://www.acjokes.com',
    city        = 'Atlantic City',
    state       = 'NJ'
WHERE id = 412;  -- AC Jokes

COMMIT;
