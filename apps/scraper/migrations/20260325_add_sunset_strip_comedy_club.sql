-- TASK-688: Add Sunset Strip Comedy Club (Austin, TX) as a new venue
-- Website: https://www.sunsetstripatx.com/
-- Sunset Strip Comedy Club (214 E 6th Street, Unit C, Austin TX) is a 21+
-- comedy club running several weekly shows.  Shows are ticketed through
-- SquadUP (user_id=9086799) and fetched via the SquadUP events API.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'Sunset Strip Comedy Club',
    '214 E 6th Street, Unit C',
    'Austin',
    'TX',
    '78701',
    'America/Chicago',
    'sunset_strip',
    TRUE,
    'https://www.sunsetstripatx.com',
    'https://www.sunsetstripatx.com/events'
);
