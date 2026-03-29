-- TASK-763: Add Big Couch New Orleans as a new venue
-- Website: https://bigcouchnola.com
-- Located at 1045 Desire Street, New Orleans, LA 70117.
-- Creative performance space offering improv/sketch comedy, theater, and other shows.
-- Primary ticketing via Eventbrite organizer ID: 29220617465

INSERT INTO clubs (name, address, city, state, zip_code, timezone, eventbrite_id, scraper, visible, website, scraping_url)
VALUES (
    'Big Couch New Orleans',
    '1045 Desire Street',
    'New Orleans',
    'LA',
    '70117',
    'America/Chicago',
    '29220617465',
    'eventbrite',
    TRUE,
    'https://bigcouchnola.com',
    'https://www.eventbrite.com/o/big-couch-29220617465'
);
