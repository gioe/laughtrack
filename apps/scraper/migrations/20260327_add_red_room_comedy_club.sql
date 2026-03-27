-- TASK-739: Add RED ROOM Comedy Club as a new venue
-- Website: https://www.redroomcomedyclub.com
-- Located at 7442 N. Western Ave, Chicago, IL 60645 (Rogers Park / West Ridge area).
-- Uses Wix native events calendar widget (not Eventbrite/inffuse).
-- compId: comp-j9ny0yyr (discovered via Playwright DOM traversal from EVENTS_ROOT_NODE).
-- No categoryId required — venue has no Wix event categories configured.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'RED ROOM Comedy Club',
    '7442 N. Western Ave',
    'Chicago',
    'IL',
    '60645',
    'America/Chicago',
    'red_room',
    TRUE,
    'https://www.redroomcomedyclub.com',
    'https://www.redroomcomedyclub.com'
);
