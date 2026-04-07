DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Zanies Comedy Night Club') THEN
        INSERT INTO "clubs" (name, address, website, scraping_url, scraper, visible, zip_code, phone_number, popularity, timezone, city, state)
        VALUES ('Zanies Comedy Night Club', '2025 8th Avenue South, Nashville, TN 37204', 'https://nashville.zanies.com', 'https://nashville.zanies.com', 'zanies', true, '37204', NULL, 0, 'America/Chicago', 'Nashville', 'TN');
    END IF;
END $$;
