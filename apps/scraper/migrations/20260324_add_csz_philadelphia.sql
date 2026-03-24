-- TASK-651: Add CSz Philadelphia (ComedySportz) as a new venue
-- CSz Philadelphia is an improv comedy club at 2030 Sansom Street in the
-- Rittenhouse neighborhood of Center City Philadelphia, operating for 25+ years.
-- Shows run every weekend; flagship show is ComedySportz (Saturdays @ 7PM).
-- Tickets are sold via VBO Tickets embedded on the club website.
-- The scraping_url stores the VBO plugin URL with the venue-specific session key.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'CSz Philadelphia',
    '2030 Sansom Street',
    'Philadelphia',
    'PA',
    '19103',
    'America/New_York',
    'csz_philadelphia',
    TRUE,
    'https://www.comedysportzphilly.com',
    'https://plugin.vbotickets.com/Plugin/events?s=4610c334-6cb9-4033-b991-1c1a89918a19'
);
