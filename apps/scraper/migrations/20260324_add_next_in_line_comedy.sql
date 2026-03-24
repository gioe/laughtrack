-- TASK-650: Add Next In Line Comedy as a new venue
-- Next In Line Comedy is a Philadelphia comedy club at 1025 Hamilton Street
-- in the Spring Garden neighborhood, opened January 2024.
-- Shows are listed via an Eventbrite organizer page (organizer ID: 35037687903).
-- The /tickets page embeds a SociableKit Eventbrite widget; all event links
-- point to eventbrite.com/o/next-in-line-comedy-35037687903.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, eventbrite_id, scraper, visible, website, scraping_url)
VALUES (
    'Next In Line Comedy',
    '1025 Hamilton Street',
    'Philadelphia',
    'PA',
    '19123',
    'America/New_York',
    '35037687903',
    'eventbrite',
    TRUE,
    'https://www.nextinlinecomedy.com',
    'https://www.eventbrite.com/o/next-in-line-comedy-35037687903'
);
