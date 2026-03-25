-- TASK-666: Add The Comedy & Magic Club as a new venue
-- The Comedy & Magic Club is located at 1018 Hermosa Ave, Hermosa Beach, CA.
-- Shows are listed via the rhp-events WordPress plugin at /events/
-- and tickets are sold through eTix (www.etix.com).

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'The Comedy & Magic Club',
    '1018 Hermosa Ave',
    'Hermosa Beach',
    'CA',
    '90254',
    'America/Los_Angeles',
    'comedy_magic_club',
    TRUE,
    'https://thecomedyandmagicclub.com',
    'https://thecomedyandmagicclub.com/events/'
);
