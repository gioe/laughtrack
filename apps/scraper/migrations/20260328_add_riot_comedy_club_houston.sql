-- TASK-752: Add The Riot Comedy Club Houston as a new venue
-- Website: https://theriothtx.com
-- Located at 2010 Waugh Drive, Houston, TX 77006.
-- Houston comedy club with nightly showcases and special events.
-- Shows are sold through Eventbrite.
-- Organizer: "The Riot Comedy Club" (organizer ID: 29979960920)

INSERT INTO clubs (name, address, city, state, zip_code, timezone, eventbrite_id, scraper, visible, website, scraping_url)
VALUES (
    'The Riot Comedy Club',
    '2010 Waugh Drive',
    'Houston',
    'TX',
    '77006',
    'America/Chicago',
    '29979960920',
    'eventbrite',
    TRUE,
    'https://theriothtx.com',
    'https://www.eventbrite.com/o/the-riot-comedy-club-29979960920'
);
