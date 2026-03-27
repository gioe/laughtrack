-- TASK-733: Add The Second City as a new venue
-- Website: https://www.secondcity.com
-- The Second City (1616 N Wells St, Chicago, IL) is the birthplace of modern
-- improvisational comedy, located in Old Town Chicago.  Has touring stand-up
-- acts and ticketed improv shows.
-- Ticketmaster venue ID discovered via Discovery API venues endpoint:
--   GET /discovery/v2/venues.json?keyword=second+city&countryCode=US&stateCode=IL
--   → KovZpZAE6EtA (Second City Mainstage, Chicago, IL)
-- Additional venues (ETC stage, Up Comedy Club) returned 0 events.
-- All show tickets link to ticketmaster.com, so scraper=live_nation.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, ticketmaster_id, scraper, visible, website, scraping_url)
VALUES (
    'The Second City',
    '1616 N Wells St',
    'Chicago',
    'IL',
    '60614',
    'America/Chicago',
    'KovZpZAE6EtA',
    'live_nation',
    TRUE,
    'https://www.secondcity.com',
    'ticketmaster/KovZpZAE6EtA'
);
