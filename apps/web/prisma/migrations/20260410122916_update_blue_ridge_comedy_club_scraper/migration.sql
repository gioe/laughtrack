-- Blue Ridge Comedy Club (club 455) moved from SeatEngine to StandUpTix.
-- Their calendar page at blueridgecomedy.com/calendar has JSON-LD Event markup,
-- so the generic json_ld scraper works. Also fill in missing location data.
UPDATE "clubs"
SET
    scraper = 'json_ld',
    scraping_url = 'https://www.blueridgecomedy.com/calendar',
    website = 'https://www.blueridgecomedy.com',
    seatengine_id = NULL,
    city = 'Bristol',
    state = 'TN',
    address = '560 English St',
    zip_code = '37620',
    timezone = 'America/New_York'
WHERE id = 455;
