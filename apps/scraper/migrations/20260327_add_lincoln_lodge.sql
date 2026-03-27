-- TASK-734: Add The Lincoln Lodge as a new venue
-- Website: https://www.thelincolnlodge.com
-- Located at 2040 N Milwaukee Ave, Chicago, IL 60647 (Logan Square).
-- Nation's longest-running independent comedy showcase. Non-profit, no drink minimum.
-- The venue website is built on Wix, with an embedded Eventbrite calendar widget.
-- The scraper queries the Eventbrite /organizers/ API directly using the organizer ID.
-- Organizer: "The Lincoln Lodge" (organizer ID: 31159352271)

INSERT INTO clubs (name, address, city, state, zip_code, timezone, eventbrite_id, scraper, visible, website, scraping_url)
VALUES (
    'The Lincoln Lodge',
    '2040 N Milwaukee Ave',
    'Chicago',
    'IL',
    '60647',
    'America/Chicago',
    '31159352271',
    'eventbrite',
    TRUE,
    'https://www.thelincolnlodge.com',
    'https://www.eventbrite.com/o/the-lincoln-lodge-31159352271'
);
