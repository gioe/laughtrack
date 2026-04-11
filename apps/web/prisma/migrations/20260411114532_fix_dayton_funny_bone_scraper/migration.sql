-- Fix Dayton Funny Bone (club 317): migrate from dead SeatEngine v1 (venue 114, HTTP 404)
-- to funny_bone scraper (Rockhouse/ETIX platform at dayton.funnybone.com);
-- fill in missing city/state/zip (Beavercreek, OH 45440)
UPDATE "clubs"
SET
    scraper = 'funny_bone',
    website = 'https://dayton.funnybone.com',
    scraping_url = 'https://dayton.funnybone.com/shows/',
    seatengine_id = NULL,
    city = 'Beavercreek',
    state = 'OH',
    zip_code = '45440',
    address = '88 Plum Street Suite 200',
    timezone = 'America/New_York'
WHERE id = 317;
