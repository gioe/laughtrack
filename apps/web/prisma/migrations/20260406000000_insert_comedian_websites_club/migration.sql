DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Comedian Websites') THEN
        INSERT INTO "clubs" (name, address, website, scraping_url, scraper, visible, zip_code, phone_number, popularity, timezone)
        VALUES ('Comedian Websites', '', '', '', 'comedian_websites', false, NULL, NULL, 0, NULL);
    END IF;
END $$;
