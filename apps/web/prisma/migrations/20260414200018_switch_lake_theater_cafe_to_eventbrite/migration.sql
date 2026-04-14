-- Switch Lake Theater & Cafe (club 1136) from SeatEngine to Eventbrite
-- Organizer: Jeff Esfeld (87504744283) — hosts "Lake Oswego Comedy Night" monthly
-- SeatEngine ID 115 returns 404; venue uses Eventbrite for comedy night ticketing

UPDATE "clubs"
SET scraper = 'eventbrite',
    eventbrite_id = '87504744283',
    seatengine_id = NULL,
    scraping_url = 'https://www.eventbrite.com/o/jeff-esfeld-87504744283'
WHERE id = 1136;
