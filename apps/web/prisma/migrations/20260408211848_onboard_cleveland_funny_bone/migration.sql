-- Onboard Cleveland Funny Bone (Cleveland, OH)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Cleveland Funny Bone') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state
        )
        VALUES (
            'Cleveland Funny Bone',
            '1148 Main Ave',
            'https://cleveland.funnybone.com',
            'https://cleveland.funnybone.com/shows/',
            'funny_bone',
            true,
            '44113',
            'America/New_York',
            'Cleveland',
            'OH'
        );
    END IF;
END $$;
