-- Insert the tour_dates platform club row so ScrapingService
-- can discover and invoke TourDatesScraper.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Tour Dates') THEN
        INSERT INTO "clubs" (name, address, website, scraping_url, scraper, visible, zip_code, phone_number, popularity, timezone)
        VALUES ('Tour Dates', '', '', 'tour_dates', 'tour_dates', false, NULL, NULL, 0, NULL);
    END IF;
END $$;
