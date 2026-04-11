-- Configure Huntsville Levity Live (club 28) scraper
-- Venue is active with 74 Ticketmaster events; scraper was null.
-- Also backfill city/state from known address.
UPDATE "clubs"
SET
    scraper = 'live_nation',
    city = 'Huntsville',
    state = 'AL',
    scraping_url = 'ticketmaster/KovZ917ARMI'
WHERE id = 28;
