-- Fix Laughing Skull scraper: migrate from seatengine (v1 ID 250, HTTP 404) to json_ld;
-- backfill location (Atlanta, GA 30309)
UPDATE "clubs"
SET
    scraper       = 'json_ld',
    scraping_url  = 'https://laughingskulllounge.com/events/',
    seatengine_id = NULL,
    website       = 'https://www.laughingskulllounge.com',
    address       = '878 Peachtree St NE',
    city          = 'Atlanta',
    state         = 'GA',
    zip_code      = '30309',
    timezone      = 'America/New_York'
WHERE id = 817;
