-- Fix The Grisly Pear Midtown (club 7): set scraper to new_york_comedy_club
-- (address-filtered JSON-LD), fix scraping_url (was missing .com domain),
-- correct zip_code from 10012 (Village) to 10019 (Midtown), and backfill city/state.
UPDATE "clubs"
SET scraper      = 'new_york_comedy_club',
    scraping_url = 'https://www.grislypearstandup.com/calendar',
    zip_code     = '10019',
    city         = 'New York',
    state        = 'NY',
    country      = 'US'
WHERE id = 7;
