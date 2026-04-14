-- Switch The Stand Up Comedy Club (club 463) from SeatEngine to TicketWeb
-- SeatEngine venue 438 returns 404 (dead); club uses TicketWeb WordPress plugin
-- Backfill location data (9831 Belmont St, Bellflower, CA 90706)
UPDATE "clubs"
SET scraper = 'ticketweb',
    scraping_url = 'https://www.thestandupclub.com/calendar/',
    seatengine_id = NULL,
    address = '9831 Belmont St',
    city = 'Bellflower',
    state = 'CA',
    zip_code = '90706',
    timezone = 'America/Los_Angeles'
WHERE id = 463;
