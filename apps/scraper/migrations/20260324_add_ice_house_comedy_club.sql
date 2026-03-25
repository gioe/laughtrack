-- TASK-672: Add Ice House Comedy Club (Pasadena, CA) as a new venue
-- Website: https://icehousecomedy.com
-- Address: 24 N Mentor Ave, Pasadena, CA 91106
-- Shows are fetched from the Tockify calendar API (calname=theicehouse).
-- Each event links to a ShowClix ticket page.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'Ice House Comedy Club',
    '24 N Mentor Ave',
    'Pasadena',
    'CA',
    '91106',
    'America/Los_Angeles',
    'ice_house',
    TRUE,
    'https://icehousecomedy.com',
    'https://tockify.com/api/ngevent?calname=theicehouse&max=200'
);
