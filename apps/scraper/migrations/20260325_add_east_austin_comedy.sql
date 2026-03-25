-- TASK-690: Add East Austin Comedy as a new venue
-- Website: https://eastaustincomedy.com/
-- East Austin Comedy is located at 2505 East 6th St. Suite D, Austin, TX 78702.
-- Intimate 82-seat BYOB comedy room running shows nightly ($10-$15 tickets).
-- Shows are booked via an embedded Square modal on the homepage (no external platform).
-- Show availability is fetched from a Netlify serverless function.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'East Austin Comedy',
    '2505 East 6th St. Suite D',
    'Austin',
    'TX',
    '78702',
    'America/Chicago',
    'east_austin_comedy',
    TRUE,
    'https://eastaustincomedy.com',
    'https://eastaustincomedy.com/'
);
