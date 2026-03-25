-- TASK-676: Add Laugh Factory Long Beach as a new venue
-- Website: https://www.laughfactory.com/long-beach
-- Laugh Factory Long Beach is located at 151 S Pine Ave, Long Beach, CA 90802.
-- Shows are sold through Eventbrite.
-- Organizer: "Laugh Factory - Long Beach" (organizer ID: 27817260251)

INSERT INTO clubs (name, address, city, state, zip_code, timezone, eventbrite_id, scraper, visible, website, scraping_url)
VALUES (
    'Laugh Factory Long Beach',
    '151 S Pine Ave',
    'Long Beach',
    'CA',
    '90802',
    'America/Los_Angeles',
    '27817260251',
    'eventbrite',
    TRUE,
    'https://www.laughfactory.com/long-beach',
    'https://www.eventbrite.com/o/laugh-factory-long-beach-27817260251'
);
