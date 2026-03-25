-- TASK-682: Add Laugh Factory Las Vegas (at Horseshoe) as a new venue
-- Website: https://www.laughfactory.com/las-vegas
-- Laugh Factory Las Vegas is at Horseshoe Las Vegas, 3645 Las Vegas Blvd South, Las Vegas, NV 89109.
-- Opened February 2026. Shows are sold through Ticketmaster.
-- Ticketmaster venue ID: KovZpZAJalFA ("Laugh Factory at Horseshoe Las Vegas")
-- Confirmed via Discovery API: 583 comedy events at this venue.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, ticketmaster_id, scraper, visible, website, scraping_url)
VALUES (
    'Laugh Factory Las Vegas',
    '3645 Las Vegas Blvd South',
    'Las Vegas',
    'NV',
    '89109',
    'America/Los_Angeles',
    'KovZpZAJalFA',
    'live_nation',
    TRUE,
    'https://www.laughfactory.com/las-vegas',
    'ticketmaster/KovZpZAJalFA'
);
