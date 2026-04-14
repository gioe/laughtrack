-- Update The Bit Theater (club 552) metadata
-- SeatEngine venue 532 is dead (0 shows); venue is active at bitimprov.org (Odoo CMS)
-- Backfill address, location, timezone, and website; clear stale SeatEngine config

UPDATE "clubs"
SET
    website = 'https://www.bitimprov.org',
    address = '4034 Fox Valley Center Dr, Aurora, IL 60504',
    city = 'Aurora',
    state = 'IL',
    zip_code = '60504',
    timezone = 'America/Chicago',
    scraping_url = 'https://www.bitimprov.org/event',
    scraper = 'pending',
    seatengine_id = NULL
WHERE id = 552;
