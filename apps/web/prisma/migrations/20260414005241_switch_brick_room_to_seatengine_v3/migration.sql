-- Switch The Brick Room (club 568) from SeatEngine v1 to v3
-- Old domain thebrickroom.cc is dead (ECONNREFUSED); old seatengine_id 548 returns 404.
-- Venue migrated to thebrickroom.org hosted on seatengine-sites.com;
-- v3 UUID: c5595eca-1589-485a-9488-e01d4d455d76.
-- Backfill address, city, state, zip, timezone from web research.
UPDATE "clubs"
SET
    scraper       = 'seatengine_v3',
    seatengine_id = 'c5595eca-1589-485a-9488-e01d4d455d76',
    website       = 'https://www.thebrickroom.org',
    scraping_url  = 'https://www.thebrickroom.org',
    address       = '942 Maple Ave, Noblesville, IN 46060',
    city          = 'Noblesville',
    state         = 'Indiana',
    zip_code      = '46060',
    timezone      = 'America/Indiana/Indianapolis'
WHERE id = 568;
