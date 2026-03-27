-- TASK-740: Add UP Comedy Club Chicago as a new venue
-- Website: https://www.secondcity.com/shows/chicago/
-- UP Comedy Club is the cabaret-style room on the 3rd floor of The Second City
-- complex at 230 W North Ave (Piper's Alley), Lincoln Park, Chicago, IL 60610.
-- Programs touring stand-up, local showcases, and improv.
--
-- Ticketing: Salesforce Sites (secondcityus.my.salesforce-sites.com/ticket/).
-- Show data comes from two Second City platform endpoints:
--   1. platform.secondcity.com/graphql — Chicago show list (venue filter)
--   2. secondcity.com/api/entityResolver — per-show instances with UTC datetimes
-- scraper=up_comedy_club handles both steps internally; scraping_url is the
-- Second City Chicago shows listing page used as the canonical source reference.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'UP Comedy Club',
    '230 W North Ave',
    'Chicago',
    'IL',
    '60610',
    'America/Chicago',
    'up_comedy_club',
    TRUE,
    'https://www.secondcity.com/shows/chicago/',
    'https://www.secondcity.com/shows/chicago/'
);
