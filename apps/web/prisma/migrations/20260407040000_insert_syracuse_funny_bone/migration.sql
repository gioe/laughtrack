DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Syracuse Funny Bone') THEN
        INSERT INTO "clubs" (name, address, website, scraping_url, scraper, visible, zip_code, phone_number, popularity, timezone, city, state)
        VALUES ('Syracuse Funny Bone', '10301 Destiny USA Dr, Syracuse, NY 13204', 'https://syracuse.funnybone.com', 'https://syracuse.funnybone.com/shows/', 'funny_bone', true, '13204', '(315) 423-8669', 0, 'America/New_York', 'Syracuse', 'NY');
    END IF;
END $$;
