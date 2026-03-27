-- TASK-738: Add The Den Theatre Chicago as a new venue
-- Multi-room performance complex in Wicker Park, Chicago.
-- Shows are listed via Squarespace GetItemsByMonth API (collectionId: 64bc3c406b6d3d1edd3c84db).
-- Ticket links are on each show's individual page (tickets.thedentheatre.com/event/*).

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'The Den Theatre',
    '1331 N Milwaukee Ave',
    'Chicago',
    'IL',
    '60622',
    'America/Chicago',
    'squarespace',
    TRUE,
    'https://thedentheatre.com',
    'https://thedentheatre.com/api/open/GetItemsByMonth?collectionId=64bc3c406b6d3d1edd3c84db'
);
