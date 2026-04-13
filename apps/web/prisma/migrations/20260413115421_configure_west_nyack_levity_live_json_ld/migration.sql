-- Configure West Nyack Levity Live (club 26) with json_ld scraper
-- Website has JSON-LD Event markup with 21+ upcoming shows (TicketWeb ticketing)
-- Populate city/state from address: 4210 Palisades Center Dr A-401, West Nyack, NY 10994
UPDATE "clubs"
SET
    scraper = 'json_ld',
    scraping_url = 'https://levitylive.com/nyack/calendar/',
    city = 'West Nyack',
    state = 'NY'
WHERE id = 26;
