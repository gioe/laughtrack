-- Switch National Lampoon The Yellow Door (club 593) from SeatEngine to Eventbrite
-- SeatEngine venue 577 returns 404 on both v1 and v2 APIs
-- Venue is active on Eventbrite with organizer 87966212103 (93 live events)
-- Location: 750 Sixth Avenue, San Diego, CA 92101

UPDATE "clubs"
SET
    scraper = 'eventbrite',
    eventbrite_id = '87966212103',
    seatengine_id = NULL,
    scraping_url = 'https://nlyellowdoor.com/sandiego/',
    address = '750 Sixth Avenue',
    city = 'San Diego',
    state = 'CA',
    zip_code = '92101',
    timezone = 'America/Los_Angeles'
WHERE id = 593;
