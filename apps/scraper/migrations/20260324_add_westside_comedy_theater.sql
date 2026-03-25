-- TASK-667: Add Westside Comedy Theater (Santa Monica) as a new venue
-- Website: https://westsidecomedy.com/
-- Also known as "M.i.'s Westside Comedy Theater"
-- Address: 1323-A 3rd Street, Santa Monica, CA 90401
-- Shows are sold through Eventbrite.
-- Organizer: "M.i.'s Westside Comedy Theater" (organizer ID: 107617136371)

INSERT INTO clubs (name, address, city, state, zip_code, timezone, eventbrite_id, scraper, visible, website, scraping_url)
VALUES (
    'Westside Comedy Theater',
    '1323-A 3rd Street',
    'Santa Monica',
    'CA',
    '90401',
    'America/Los_Angeles',
    '107617136371',
    'eventbrite',
    TRUE,
    'https://westsidecomedy.com',
    'https://www.eventbrite.com/o/westside-comedy-theater-107617136371'
);
