-- TASK-732: Add Zanies Comedy Club as a new venue
-- Website: https://chicago.zanies.com
-- Zanies Comedy Club (1548 N Wells St, Chicago, IL) is a Chicago institution
-- operating since 1978 in the Old Town neighbourhood.  Shows run seven nights
-- a week.  Event data is served via the rhp-events WordPress plugin: headliner
-- runs appear as series pages and one-off specials as individual show pages.
-- Tickets are sold through Etix (partner_id=100).

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'Zanies Comedy Club',
    '1548 N Wells St',
    'Chicago',
    'IL',
    '60610',
    'America/Chicago',
    'zanies',
    TRUE,
    'https://chicago.zanies.com',
    'https://chicago.zanies.com'
);
