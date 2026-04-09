-- TASK-1108: Fix AC Jokes (id=412) — switch from dead SeatEngine to Wix Events.
--
-- Investigation findings:
--   - Original SeatEngine subdomain (4bc8f310-...seatengine.com) is defunct:
--     API returns 404, events page shows 0 events
--   - Real website is acjokes.com (Wix site), calendar uses Wix Events widget
--     (comp-lpdlygbr, schedule-page variant with EVENTS_ROOT_NODE)
--   - 111 shows scraped successfully across 4 venues (Resorts Casino,
--     The Hook at Caesars, The Cove Brigantine, Hi Point Pub Absecon)
--   - Club was missing city/state/timezone metadata
--
-- Action: switch scraper to wix_events, set comp_id, update URLs and metadata.

BEGIN;

UPDATE clubs
SET scraper      = 'wix_events',
    wix_comp_id  = 'comp-lpdlygbr',
    website      = 'https://www.acjokes.com',
    scraping_url = 'https://www.acjokes.com',
    city         = 'Atlantic City',
    state        = 'NJ',
    timezone     = 'America/New_York'
WHERE id = 412;  -- AC Jokes

COMMIT;
