-- TASK-652: Add Philly Improv Theater (PHIT) as a new venue
-- Website: https://www.phillyimprovtheater.com/
-- Shows are fetched via the Crowdwork/Fourthwall Tickets API embedded in the
-- PHIT homepage via <script src="https://fourthwalltickets.com/embed.js?v=5"
--   data-theatre="phillyimprovtheater" data-type="shows">.
-- The widget calls: https://crowdwork.com/api/v2/phillyimprovtheater/shows
-- PHIT runs seasonal showcase events (PHEST) at the end of each class session.
-- Venue location: Hamilton Family Arts Center, 62 N 2nd St, Philadelphia, PA.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'Philly Improv Theater',
    '62 N 2nd St',
    'Philadelphia',
    'PA',
    '19106',
    'America/New_York',
    'philly_improv_theater',
    TRUE,
    'https://www.phillyimprovtheater.com',
    'https://crowdwork.com/api/v2/phillyimprovtheater/shows'
);
