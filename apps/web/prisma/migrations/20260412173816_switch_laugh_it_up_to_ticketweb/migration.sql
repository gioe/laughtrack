-- Switch LAUGH IT UP COMEDY CLUB (club 485) from live_nation to ticketweb scraper
-- Scrapes directly from the club's calendar page (WordPress + TicketWeb plugin)
-- so show_page_url drives traffic to the club's own site
UPDATE "clubs"
SET
    scraper = 'ticketweb',
    scraping_url = 'https://www.laughitupcomedy.com/calendar/',
    ticketmaster_id = NULL
WHERE id = 485;
