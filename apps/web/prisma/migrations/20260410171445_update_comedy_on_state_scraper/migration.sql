-- Update Comedy on State (club 435) — switch from SeatEngine (venue 410, HTTP 404) to json_ld scraper
-- Venue is active at madisoncomedy.com with ETIX ticketing and JSON-LD Event markup on homepage
UPDATE "clubs"
SET
    scraper = 'json_ld',
    scraping_url = 'https://www.madisoncomedy.com',
    seatengine_id = NULL,
    city = 'Madison',
    state = 'WI',
    zip_code = '53703',
    address = '202 State Street, Lower Level',
    timezone = 'America/Chicago'
WHERE id = 435;
