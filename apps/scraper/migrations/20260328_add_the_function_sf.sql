-- TASK-745: Add The Function SF as a new venue
-- Website: https://www.thefunctionsf.com
-- SeatEngine site: https://the-function.seatengine-sites.com
-- Located at 1414 Market Street, San Francisco, CA 94102.
-- Black-owned comedy club featuring recurring weekly shows.
-- Uses classic SeatEngine platform (cdn.seatengine.com HTML, not the REST API).
-- Venue ID 540 derived from logo URL: files.seatengine.com/styles/logos/540/original/
-- Events page returns 16+ shows with Layout 1 HTML (event-times-group) per extractor.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, seatengine_id, scraper, visible, website, scraping_url)
VALUES (
    'The Function SF',
    '1414 Market Street',
    'San Francisco',
    'CA',
    '94102',
    'America/Los_Angeles',
    '540',
    'seatengine_classic',
    TRUE,
    'https://www.thefunctionsf.com',
    'the-function.seatengine-sites.com/events'
);
