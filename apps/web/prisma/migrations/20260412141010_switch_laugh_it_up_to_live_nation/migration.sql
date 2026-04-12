-- Switch LAUGH IT UP COMEDY CLUB (club 485) from SeatEngine to Live Nation (TicketWeb/Ticketmaster)
-- SeatEngine API venue 461 returns 404; venue now sells via TicketWeb (Ticketmaster property)
-- Ticketmaster Discovery API venue ID: KovZpZAkIJlA (10 upcoming events confirmed)
UPDATE "clubs"
SET
    scraper = 'live_nation',
    ticketmaster_id = 'KovZpZAkIJlA',
    seatengine_id = NULL,
    scraping_url = 'https://www.laughitupcomedy.com',
    address = '35 Main St',
    city = 'Poughkeepsie',
    state = 'NY',
    zip_code = '12601',
    timezone = 'America/New_York'
WHERE id = 485;
