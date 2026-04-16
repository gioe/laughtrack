-- Adopt The Comedy Club On State (club 826) — Madison, WI.
-- Switch scraper from stale SeatEngine (venue_id=265 — returns 0 shows) to json_ld
-- against the club's own WordPress site, which publishes 26+ upcoming events in
-- JSON-LD Event markup on /events. Clear stale seatengine_id, refresh metadata,
-- and unhide.
UPDATE clubs
SET
    scraper = 'json_ld',
    scraping_url = 'https://www.madisoncomedy.com/events',
    website = 'https://www.madisoncomedy.com',
    seatengine_id = NULL,
    address = '202 State Street, Lower Level',
    city = 'Madison',
    state = 'WI',
    zip_code = '53703',
    timezone = 'America/Chicago',
    visible = true
WHERE id = 826;
