-- Switch The Comedy Cave (club 818) from SeatEngine to Showpass (comedy_cave scraper)
-- SeatEngine venue 251 returns 404; venue uses Showpass widget (venue ID 15525)
-- Backfill address, city, state, timezone, website (HTTPS)
UPDATE "clubs"
SET
    scraper       = 'comedy_cave',
    scraping_url  = 'https://comedycave.com/shows/',
    website       = 'https://comedycave.com',
    address       = '1020 8th Avenue SW',
    city          = 'Calgary',
    state         = 'AB',
    zip_code      = 'T2P 1J2',
    timezone      = 'America/Edmonton',
    country       = 'CA',
    seatengine_id = NULL
WHERE id = 818;
