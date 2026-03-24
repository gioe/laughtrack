-- TASK-649: Add Punch Line Philly as a new venue
-- Website: https://www.punchlinephilly.com/
-- Ticketmaster venue ID discovered via Discovery API venues endpoint:
--   GET /discovery/v2/venues.json?keyword=punch+line+philly&countryCode=US
--   → KovZpZAEvtFA (Punch Line Philly, Philadelphia, PA)
-- All show tickets link to ticketmaster.com, so scraper=live_nation.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, ticketmaster_id, scraper, visible, website, scraping_url)
VALUES (
    'Punch Line Philly',
    '33 E. Laurel Street',
    'Philadelphia',
    'PA',
    '19123',
    'America/New_York',
    'KovZpZAEvtFA',
    'live_nation',
    TRUE,
    'https://www.punchlinephilly.com',
    'ticketmaster/KovZpZAEvtFA'
);
