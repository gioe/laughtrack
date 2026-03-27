-- TASK-737: Add The Comedy Bar Chicago as a new venue
-- Website: https://comedybar.com
-- Located at 162 E Superior St, Chicago, IL 60611 (River North, inside Gino's East).
-- Two stages, 100+ seats each. Nightly stand-up shows with local and national acts.
-- Shows are sold through Eventbrite.
-- Organizer: "The Comedy Bar Chicago" (organizer ID: 17584944942)

INSERT INTO clubs (name, address, city, state, zip_code, timezone, eventbrite_id, scraper, visible, website, scraping_url)
VALUES (
    'The Comedy Bar Chicago',
    '162 E Superior St',
    'Chicago',
    'IL',
    '60611',
    'America/Chicago',
    '17584944942',
    'eventbrite',
    TRUE,
    'https://comedybar.com',
    'https://www.eventbrite.com/o/the-comedy-bar-chicago-17584944942'
);
