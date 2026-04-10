-- Switch Comedy Blvd (club 510) from dead SeatEngine to Eventbrite
-- SeatEngine venue 486 returns HTTP 404; website comedyblvdla.com ECONNREFUSED
-- Eventbrite organizer 43929578463 has 378 past events (0 upcoming as of 2026-04-10)
UPDATE "clubs"
SET
    scraper = 'eventbrite',
    eventbrite_id = '43929578463',
    seatengine_id = NULL,
    scraping_url = 'https://www.eventbrite.com/o/comedy-blvd-43929578463',
    address = '7924 Beverly Blvd',
    city = 'Los Angeles',
    state = 'CA',
    zip_code = '90048',
    timezone = 'America/Los_Angeles'
WHERE id = 510;
