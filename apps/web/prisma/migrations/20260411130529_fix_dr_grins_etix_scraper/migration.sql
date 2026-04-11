-- Fix Dr. Grins Comedy Club (club 207) — switched from SeatEngine to Etix
-- grinstix.com now 301-redirects to etix.com/ticket/v/35455/...
-- Fill missing city/state/zip/timezone, update scraper to dr_grins (Etix),
-- clear dead SeatEngine config, update website to canonical URL.
UPDATE "clubs"
SET
    scraper = 'dr_grins',
    scraping_url = 'https://www.etix.com/ticket/v/35455/drgrins-comedy-club-at-the-bob',
    website = 'https://www.thebob.com/drgrins/',
    seatengine_id = NULL,
    city = 'Grand Rapids',
    state = 'MI',
    zip_code = '49503',
    timezone = 'America/Detroit'
WHERE id = 207;
