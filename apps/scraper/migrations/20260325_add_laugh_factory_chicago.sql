-- TASK-676: Add Laugh Factory Chicago as a new venue
-- Website: https://www.laughfactory.com/chicago
-- Laugh Factory Chicago is located at 3175 N Broadway, Chicago, IL 60657.
-- Shows are sold through Eventbrite.
-- Organizer: "Laugh Factory - Chicago" (organizer ID: 27398316027)

INSERT INTO clubs (name, address, city, state, zip_code, timezone, eventbrite_id, scraper, visible, website, scraping_url)
VALUES (
    'Laugh Factory Chicago',
    '3175 N Broadway',
    'Chicago',
    'IL',
    '60657',
    'America/Chicago',
    '27398316027',
    'eventbrite',
    TRUE,
    'https://www.laughfactory.com/chicago',
    'https://www.eventbrite.com/o/laugh-factory-chicago-27398316027'
);
