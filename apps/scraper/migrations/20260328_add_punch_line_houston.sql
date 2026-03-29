-- TASK-751: Add Punch Line Comedy Club Houston as a new venue
-- Website: https://www.punchlinehtx.com/
-- Located at 1204 Caroline Street, Houston, TX 77002.
-- Houston comedy club in the Punch Line family.
-- Ticketmaster venue ID discovered via Discovery API venues endpoint:
--   GET /discovery/v2/venues.json?keyword=punch+line+houston&countryCode=US
--   → KovZ917ARGO (Punch Line Houston, Houston, TX)
-- All show tickets link to ticketmaster.com, so scraper=live_nation.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, ticketmaster_id, scraper, visible, website, scraping_url)
VALUES (
    'Punch Line Comedy Club Houston',
    '1204 Caroline Street',
    'Houston',
    'TX',
    '77002',
    'America/Chicago',
    'KovZ917ARGO',
    'live_nation',
    TRUE,
    'https://www.punchlinehtx.com',
    'ticketmaster/KovZ917ARGO'
);
