-- Onboard Punch Line Irving (Irving, TX)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Punch Line Irving') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state, ticketmaster_id
        )
        VALUES (
            'Punch Line Irving',
            '310 W Las Colinas Blvd., Suite 130, Irving, TX 75039',
            'https://www.punchlineirving.com',
            'https://www.punchlineirving.com/shows',
            'live_nation',
            true,
            '75039',
            'America/Chicago',
            'Irving',
            'TX',
            'KovZ917AYIC'
        );
    END IF;
END $$;
