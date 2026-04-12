-- Fix Let's Comedy Venues (club 410): migrate from seatengine (v1 ID 385, HTTP 404) to json_ld;
-- backfill location (Indianapolis, IN 46203)
UPDATE "clubs"
SET
    scraper = 'json_ld',
    scraping_url = 'https://www.letscomedyftw.com/events',
    website = 'https://www.letscomedyftw.com',
    seatengine_id = NULL,
    address = '1116 Prospect St',
    city = 'Indianapolis',
    state = 'IN',
    zip_code = '46203',
    timezone = 'America/Indiana/Indianapolis',
    visible = true
WHERE id = 410;
