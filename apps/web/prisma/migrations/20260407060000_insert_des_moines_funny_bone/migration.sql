DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Des Moines Funny Bone') THEN
        INSERT INTO "clubs" (name, address, website, scraping_url, scraper, visible, zip_code, phone_number, popularity, timezone, city, state)
        VALUES ('Des Moines Funny Bone', '560 S Prairie View Dr, West Des Moines, IA 50266', 'https://desmoines.funnybone.com', 'https://desmoines.funnybone.com/shows/', 'funny_bone', true, '50266', '(515) 270-2100', 0, 'America/Chicago', 'West Des Moines', 'IA');
    END IF;
END $$;
