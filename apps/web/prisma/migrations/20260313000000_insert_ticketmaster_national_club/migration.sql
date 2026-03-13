-- Insert the ticketmaster_national platform club row so ScrapingService
-- can discover and invoke TicketmasterNationalScraper.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE scraper = 'ticketmaster_national') THEN
        INSERT INTO "clubs" (name, address, website, scraping_url, scraper, visible, zip_code, phone_number, popularity, timezone)
        VALUES ('Ticketmaster National', '', '', 'www.ticketmaster.com', 'ticketmaster_national', true, '', '', 0, NULL);
    END IF;
END $$;
