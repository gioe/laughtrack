DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Omaha Funny Bone') THEN
        INSERT INTO "clubs" (name, address, website, scraping_url, scraper, visible, zip_code, phone_number, popularity, timezone, city, state)
        VALUES ('Omaha Funny Bone', '710 N 114th St Suite 210, Omaha, NE 68154', 'https://omaha.funnybone.com', 'https://omaha.funnybone.com/shows/', 'improv', true, '68154', '(402) 493-8036', 0, 'America/Chicago', 'Omaha', 'NE');
    END IF;
END $$;
