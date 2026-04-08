-- Onboard Tampa Funny Bone (Tampa, FL)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Tampa Funny Bone') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state
        )
        VALUES (
            'Tampa Funny Bone',
            '1600 E 8th Ave C-112',
            'https://tampa.funnybone.com',
            'https://tampa.funnybone.com/shows/',
            'funny_bone',
            true,
            '33605',
            'America/New_York',
            'Tampa',
            'FL'
        );
    END IF;
END $$;
