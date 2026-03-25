-- TASK-669: Add The Elysian Theater as a new venue
-- The Elysian is a live performance venue in Los Angeles (Silver Lake/Atwater Village).
-- Shows are listed via Squarespace GetItemsByMonth API (collectionId: 613af44feffe2b7f78a46b63).

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'The Elysian Theater',
    '1944 Riverside Drive',
    'Los Angeles',
    'CA',
    '90039',
    'America/Los_Angeles',
    'elysian_theater',
    TRUE,
    'https://www.elysiantheater.com',
    'https://www.elysiantheater.com/api/open/GetItemsByMonth'
);
