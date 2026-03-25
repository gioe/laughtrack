-- TASK-689: Add The Creek and The Cave as a new venue
-- Austin comedy club, every-night shows, known as the local comics' hangout.
-- Website: https://www.creekandcave.com/
-- Event data: S3 monthly JSON at creekandcaveevents.s3.amazonaws.com/events/month/
-- Tickets: Showclix (links embedded in S3 data)

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'The Creek and The Cave',
    '611 East 7th St',
    'Austin',
    'TX',
    '78701',
    'America/Chicago',
    'creek_and_cave',
    TRUE,
    'https://www.creekandcave.com',
    'https://www.creekandcave.com/calendar'
);
