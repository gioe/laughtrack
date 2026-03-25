-- TASK-676: Add Laugh Factory San Diego as a new venue
-- Website: https://www.laughfactory.com/san-diego
-- Laugh Factory San Diego is located at 432 F St, San Diego, CA 92101.
-- Shows are sold through Eventbrite.
-- Organizer: "Laugh Factory - San Diego" (organizer ID: 18637206571)

INSERT INTO clubs (name, address, city, state, zip_code, timezone, eventbrite_id, scraper, visible, website, scraping_url)
VALUES (
    'Laugh Factory San Diego',
    '432 F St',
    'San Diego',
    'CA',
    '92101',
    'America/Los_Angeles',
    '18637206571',
    'eventbrite',
    TRUE,
    'https://www.laughfactory.com/san-diego',
    'https://www.eventbrite.com/o/laugh-factory-san-diego-18637206571'
);
