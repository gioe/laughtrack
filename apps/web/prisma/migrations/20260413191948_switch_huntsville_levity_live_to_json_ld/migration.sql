-- Switch Huntsville Levity Live from live_nation to json_ld scraper
-- Calendar page has JSON-LD Event data with TicketWeb purchase URLs
UPDATE "clubs"
SET
    scraper = 'json_ld',
    scraping_url = 'https://levitylive.com/huntsville/calendar/',
    ticketmaster_id = NULL
WHERE id = 28;
