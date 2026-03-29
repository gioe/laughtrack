-- TASK-761: Add Comedy House NOLA as a closed venue
-- The venue permanently closed. Domain (comedyhousenola.com) has been taken
-- over by an unrelated party. Yelp confirms closed as of March 2026.
-- Source: https://www.facebook.com/OpenMicFromHell/posts/...562263716555589/

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url, status, closed_at)
VALUES (
    'Comedy House NOLA',
    '609 Fulton St',
    'New Orleans',
    'LA',
    '70130',
    'America/Chicago',
    NULL,
    FALSE,
    'https://comedyhousenola.com',
    'https://comedyhousenola.com',
    'closed',
    '2026-03-01T00:00:00Z'
);
