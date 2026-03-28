-- TASK-744: Add Cobb's Comedy Club as a new venue
-- Website: https://www.cobbscomedy.com (cobbscomedyclub.com redirects here)
-- Located at 915 Columbus Ave, San Francisco, CA 94133.
-- San Francisco's premier comedy club, featuring national touring headliners.
-- Ticketmaster venue ID discovered via Discovery API venues endpoint:
--   GET /discovery/v2/venues.json?keyword=cobbs+comedy&countryCode=US
--   → KovZpZAEkFEA (Cobb's Comedy Club, San Francisco, CA)
-- All show tickets link to ticketmaster.com, so scraper=live_nation.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, ticketmaster_id, scraper, visible, website, scraping_url)
VALUES (
    'Cobb''s Comedy Club',
    '915 Columbus Ave',
    'San Francisco',
    'CA',
    '94133',
    'America/Los_Angeles',
    'KovZpZAEkFEA',
    'live_nation',
    TRUE,
    'https://www.cobbscomedy.com',
    'ticketmaster/KovZpZAEkFEA'
);
