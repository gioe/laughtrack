-- Configure Oxnard Levity Live (club 27) with json_ld scraper
-- Website has JSON-LD Event markup with 26+ upcoming shows (TicketWeb ticketing)
-- Populate city/state from address: 591 Collection Blvd, Oxnard, CA 93036
UPDATE "clubs"
SET
    scraper = 'json_ld',
    scraping_url = 'https://levitylive.com/oxnard/calendar/',
    city = 'Oxnard',
    state = 'CA'
WHERE id = 27;
