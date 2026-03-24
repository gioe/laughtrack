-- TASK-665: Add Laugh Factory Hollywood as a new venue
-- Website: https://www.laughfactory.com/
-- Laugh Factory Hollywood is the flagship location at 8001 W Sunset Blvd,
-- Los Angeles, CA 90046. Shows are sold through Eventbrite.
-- Organizer: "Laugh Factory - Hollywood" (organizer ID: 18525142576)
-- The /venues/{venue_id} endpoint also works (venue ID: 28808914) but
-- the organizer ID ensures all shows across event types are captured.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, eventbrite_id, scraper, visible, website, scraping_url)
VALUES (
    'Laugh Factory Hollywood',
    '8001 W Sunset Blvd',
    'Los Angeles',
    'CA',
    '90046',
    'America/Los_Angeles',
    '18525142576',
    'eventbrite',
    TRUE,
    'https://www.laughfactory.com',
    'https://www.eventbrite.com/o/laugh-factory-hollywood-18525142576'
);
