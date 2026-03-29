-- TASK-750: Add Third Coast Comedy Club as a new venue
-- Website: https://www.thirdcoastcomedy.club
-- Located at 1310 Clinton Street, Suite 121, Nashville, TN 37203
-- Nashville comedy club using Vivenu ticketing platform.
-- Show listing embedded in Vivenu seller page __NEXT_DATA__ JSON.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'Third Coast Comedy Club',
    '1310 Clinton Street, Suite 121',
    'Nashville',
    'TN',
    '37203',
    'America/Chicago',
    'vivenu',
    TRUE,
    'https://www.thirdcoastcomedy.club',
    'https://tickets.thirdcoastcomedy.club/'
);
