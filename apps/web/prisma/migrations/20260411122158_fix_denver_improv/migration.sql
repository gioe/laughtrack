-- Fix Denver Improv (club 56) — set live_nation scraper, fill missing location
UPDATE "clubs"
SET
    scraper = 'live_nation',
    scraping_url = 'ticketmaster/KovZpZAknAFA',
    address = '8246 E Northfield Blvd Unit 1400',
    city = 'Denver',
    state = 'CO',
    zip_code = '80238',
    timezone = 'America/Denver',
    website = 'https://improv.com/denver/'
WHERE id = 56;
