-- Configure Improbable Comedy (club 809) — switch from seatengine to eventbrite scraper
-- Venue uses Eventbrite organizer 10899180919; SeatEngine ID 238 is stale (0 events)
-- Location: Silver Spring, MD (produces shows at various DMV venues)
UPDATE "clubs"
SET
    scraper = 'eventbrite',
    eventbrite_id = '10899180919',
    seatengine_id = NULL,
    website = 'https://www.improbablecomedy.com',
    scraping_url = 'https://www.eventbrite.com/o/improbable-comedy-10899180919',
    city = 'Silver Spring',
    state = 'MD'
WHERE id = 809;
