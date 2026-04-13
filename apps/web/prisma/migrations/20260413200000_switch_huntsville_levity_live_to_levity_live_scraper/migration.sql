-- Switch Huntsville Levity Live from live_nation to custom levity_live scraper
-- Two-pass scraper: calendar page JSON-LD for event list + comic detail pages for per-showtime data
-- Ticket URLs point to ticketweb.com, show_page_url points to levitylive.com
UPDATE "clubs"
SET
    scraper = 'levity_live',
    scraping_url = 'https://levitylive.com/huntsville/calendar/',
    ticketmaster_id = NULL
WHERE id = 28;
