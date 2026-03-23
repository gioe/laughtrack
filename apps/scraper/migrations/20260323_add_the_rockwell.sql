-- TASK-562: Add The Rockwell as a new venue
-- The Rockwell is a 200-cap black-box theater in Somerville, MA (Davis Square).
-- Shows are listed via The Events Calendar WordPress plugin REST API.
-- Scraper fetches /wp-json/tribe/events/v1/events with pagination.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'The Rockwell',
    '255 Elm St',
    'Somerville',
    'MA',
    '02144',
    'America/New_York',
    'the_rockwell',
    TRUE,
    'https://therockwell.org',
    'https://therockwell.org/wp-json/tribe/events/v1/events'
);
