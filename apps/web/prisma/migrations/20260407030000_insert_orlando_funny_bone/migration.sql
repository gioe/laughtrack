DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Orlando Funny Bone') THEN
        INSERT INTO "clubs" (name, address, website, scraping_url, scraper, visible, zip_code, phone_number, popularity, timezone, city, state)
        VALUES ('Orlando Funny Bone', '9101 International Dr Suite 2310, Orlando, FL 32819', 'https://orlando.funnybone.com', 'https://orlando.funnybone.com/shows/', 'funny_bone', true, '32819', '(407) 480-5233', 0, 'America/New_York', 'Orlando', 'FL');
    END IF;
END $$;
