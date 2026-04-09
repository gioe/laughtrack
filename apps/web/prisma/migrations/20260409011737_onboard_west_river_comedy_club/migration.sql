-- Onboard West River Comedy Club (Rapid City, SD)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'West River Comedy Club') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state
        )
        VALUES (
            'West River Comedy Club',
            '632 1/2 St Joseph St, Rapid City, SD 57701',
            'https://www.westrivercomedy.com',
            'https://www.westrivercomedy.com',
            'wix_events',
            true,
            '57701',
            'America/Denver',
            'Rapid City',
            'SD'
        );
    END IF;
END $$;
