-- Fix Funny Bone Columbus (club 308): migrate from dead SeatEngine v1 (venue 105)
-- to funny_bone scraper (Rockhouse/ETIX at columbus.funnybone.com)
UPDATE "clubs"
SET
    scraper = 'funny_bone',
    website = 'https://columbus.funnybone.com',
    scraping_url = 'https://columbus.funnybone.com/shows/',
    seatengine_id = NULL,
    timezone = 'America/New_York'
WHERE id = 308;

-- Fix Richmond Funny Bone (club 1034): migrate from tour_dates
-- to funny_bone scraper (Rockhouse/ETIX at richmond.funnybone.com)
UPDATE "clubs"
SET
    scraper = 'funny_bone',
    website = 'https://richmond.funnybone.com',
    scraping_url = 'https://richmond.funnybone.com/shows/',
    timezone = 'America/New_York'
WHERE id = 1034;
