-- Switch Albany Funny Bone (club 323) from dead SeatEngine to funny_bone scraper
-- SeatEngine URL (funny-albany.seatengine.com) redirects to generic seatengine.com (302).
-- Venue is live at albany.funnybone.com with shows via Rockhouse Partners / Etix.
UPDATE "clubs"
SET
    scraper = 'funny_bone',
    scraping_url = 'https://albany.funnybone.com/shows/',
    website = 'https://albany.funnybone.com',
    city = 'Albany',
    state = 'NY',
    zip_code = '12203',
    timezone = 'America/New_York',
    seatengine_id = NULL
WHERE id = 323;
