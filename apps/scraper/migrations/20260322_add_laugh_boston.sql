-- TASK-557: Add Laugh Boston as a new venue
-- Laugh Boston is a 300-seat comedy club in Boston's Seaport District.
-- Shows are listed as Tixr links on the homepage (tixr.com/groups/laughboston/events/*).
-- Scraper fetches laughboston.com homepage, extracts Tixr URLs, and uses TixrClient.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'Laugh Boston',
    '425 Summer St',
    'Boston',
    'MA',
    '02210',
    'America/New_York',
    'laugh_boston',
    TRUE,
    'https://laughboston.com',
    'https://laughboston.com'
);
