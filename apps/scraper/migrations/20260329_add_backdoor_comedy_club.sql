-- TASK-757: Add Backdoor Comedy Club as a new venue
-- Website: https://www.backdoorcomedy.com/
-- Located at 940 E Belt Line Rd, Richardson, TX 75081 (inside Doubletree by Hilton).
-- Regular shows: Thursdays (Open Mic 8 PM), Fridays (8:30 PM), Saturdays (8 PM).
-- Primary ticketing via Eventbrite organizer ID: 86805735233

INSERT INTO clubs (name, address, city, state, zip_code, timezone, eventbrite_id, scraper, visible, website, scraping_url)
VALUES (
    'Backdoor Comedy Club',
    '940 E Belt Line Rd',
    'Richardson',
    'TX',
    '75081',
    'America/Chicago',
    '86805735233',
    'eventbrite',
    TRUE,
    'https://www.backdoorcomedy.com',
    'https://www.eventbrite.com/o/backdoor-comedy-club-86805735233'
);
