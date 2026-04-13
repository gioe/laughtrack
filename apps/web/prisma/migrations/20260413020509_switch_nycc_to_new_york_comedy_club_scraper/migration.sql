-- Switch all three New York Comedy Club venues to the new_york_comedy_club scraper
-- which filters JSON-LD events by street address, replacing the generic json_ld
-- scraper (club 2) and null scrapers (clubs 3, 4) that couldn't distinguish locations.

UPDATE "clubs"
SET scraper = 'new_york_comedy_club',
    scraping_url = 'https://newyorkcomedyclub.com/calendar',
    city = 'New York',
    state = 'NY',
    timezone = 'America/New_York'
WHERE id IN (2, 3, 4);
