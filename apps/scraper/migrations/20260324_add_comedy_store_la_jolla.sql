-- TASK-675: Add The Comedy Store La Jolla as a new venue
-- Website: https://thecomedystore.com/la-jolla/
-- The Comedy Store La Jolla (8971 Villa La Jolla Dr, La Jolla, CA 92037) uses
-- the same day-by-day HTML calendar structure as the West Hollywood location.
-- Reuses the comedy_store scraper; scraping_url points to the La Jolla calendar.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'The Comedy Store La Jolla',
    '8971 Villa La Jolla Dr',
    'La Jolla',
    'CA',
    '92037',
    'America/Los_Angeles',
    'comedy_store',
    TRUE,
    'https://thecomedystore.com/la-jolla',
    'https://thecomedystore.com/la-jolla/calendar'
);
