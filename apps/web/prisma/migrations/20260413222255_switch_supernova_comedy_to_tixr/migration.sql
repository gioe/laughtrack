-- Switch SuperNova Comedy (club 456) from seatengine to tixr scraper
-- SeatEngine venue 431 returns 404; venue now uses Tixr (tixr.com/groups/supernova)
-- Also populate address, city, state, zip_code, timezone (previously empty)
UPDATE "clubs"
SET
    scraper = 'tixr',
    scraping_url = 'https://www.tixr.com/groups/supernova',
    seatengine_id = NULL,
    address = '1716 Whitley Ave',
    city = 'Los Angeles',
    state = 'CA',
    zip_code = '90028',
    timezone = 'America/Los_Angeles'
WHERE id = 456;
