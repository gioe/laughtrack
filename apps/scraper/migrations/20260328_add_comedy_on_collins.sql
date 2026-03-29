-- TASK-753: Add Comedy on Collins as a new venue
-- Website: https://www.comedyoncollins.com
-- Located at 6752 Collins Avenue, Miami Beach, FL 33141.
-- Miami Beach comedy venue hosting weekly stand-up showcases.
-- Shows are sold through Eventbrite.
-- Organizer: "Comedy on Collins" (organizer ID: 109625487101)

INSERT INTO clubs (name, address, city, state, zip_code, timezone, eventbrite_id, scraper, visible, website, scraping_url)
VALUES (
    'Comedy on Collins',
    '6752 Collins Avenue',
    'Miami Beach',
    'FL',
    '33141',
    'America/New_York',
    '109625487101',
    'eventbrite',
    TRUE,
    'https://www.comedyoncollins.com',
    'https://www.eventbrite.com/o/comedy-on-collins-109625487101'
);
