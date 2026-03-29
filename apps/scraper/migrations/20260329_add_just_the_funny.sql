-- TASK-755: Add Just the Funny as a new venue
-- Website: http://www.justthefunny.com
-- Located at 3119 Coral Way, Miami, FL 33145.
-- Miami comedy club / improv theater.
-- Ticketmaster venue ID discovered via Discovery API venues endpoint:
--   GET /discovery/v2/venues.json?keyword=Just+the+Funny&countryCode=US
--   → KovZpZAFJEvA (Just the Funny, Miami, FL)
-- Tickets sold via TicketWeb (a Ticketmaster subsidiary) — scraper=live_nation.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, ticketmaster_id, scraper, visible, website, scraping_url)
VALUES (
    'Just the Funny',
    '3119 Coral Way',
    'Miami',
    'FL',
    '33145',
    'America/New_York',
    'KovZpZAFJEvA',
    'live_nation',
    TRUE,
    'http://www.justthefunny.com',
    'ticketmaster/KovZpZAFJEvA'
);
