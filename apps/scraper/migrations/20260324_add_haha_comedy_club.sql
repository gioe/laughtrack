-- TASK-668: Add HAHA Comedy Club (North Hollywood, CA) as a new venue
-- Website: https://www.hahacomedyclub.com/
-- Address: 4712 Lankershim Blvd, North Hollywood, CA 91602
-- Shows are listed at hahacomedyclub.com/calendar with Tixr (tixr.com/groups/hahacomedyclub) ticket links.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'HAHA Comedy Club',
    '4712 Lankershim Blvd',
    'North Hollywood',
    'CA',
    '91602',
    'America/Los_Angeles',
    'haha_comedy_club',
    TRUE,
    'https://www.hahacomedyclub.com',
    'https://www.hahacomedyclub.com/calendar'
);
