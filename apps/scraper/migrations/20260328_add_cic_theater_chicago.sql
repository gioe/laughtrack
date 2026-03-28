-- TASK-743: Add CIC Theater Chicago as a new venue
-- Website: https://www.cictheater.com
-- Located at 1422 W Irving Park Rd, Chicago, IL 60613 (Wrigleyville/North Center).
-- Chicago improv, sketch, and theatrical comedy venue with training programs.
-- Shows are sold through Eventbrite.
-- Organizer: "CIC Theater" (organizer ID: 34074498445)

INSERT INTO clubs (name, address, city, state, zip_code, timezone, eventbrite_id, scraper, visible, website, scraping_url)
VALUES (
    'CIC Theater',
    '1422 W Irving Park Rd',
    'Chicago',
    'IL',
    '60613',
    'America/Chicago',
    '34074498445',
    'eventbrite',
    TRUE,
    'https://www.cictheater.com',
    'https://www.eventbrite.com/o/cic-theater-34074498445'
);
