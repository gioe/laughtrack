-- Onboard Revolution Hall (Portland, OR)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Revolution Hall') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state
        )
        VALUES (
            'Revolution Hall',
            '1300 SE Stark St, Portland, OR 97214',
            'https://www.revolutionhall.com',
            'https://www.revolutionhall.com/',
            'revolution_hall',
            true,
            '97214',
            'America/Los_Angeles',
            'Portland',
            'OR'
        );
    END IF;
END $$;
