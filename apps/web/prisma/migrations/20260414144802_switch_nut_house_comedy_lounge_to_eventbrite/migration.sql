-- Switch The Nut House Comedy Lounge (club 452) from SeatEngine to Eventbrite
-- SeatEngine venue 427 redirects to generic seatengine.com (dead)
-- Eventbrite organizer 29594655531 has 3 upcoming + 102 past events
-- Also backfill missing location data (North Little Rock, AR)

UPDATE "clubs"
SET
    scraper = 'eventbrite',
    eventbrite_id = '29594655531',
    seatengine_id = NULL,
    scraping_url = 'https://www.eventbrite.com/o/the-nut-house-comedy-lounge-29594655531',
    website = 'https://www.eventbrite.com/o/the-nut-house-comedy-lounge-29594655531',
    address = '303 Phillips Rd',
    city = 'North Little Rock',
    state = 'AR',
    zip_code = '72117',
    timezone = 'America/Chicago'
WHERE id = 452;
