-- Onboard Jimmy Kimmel's Comedy Club (Las Vegas, NV)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Jimmy Kimmel''s Comedy Club') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state, ticketmaster_id
        )
        VALUES (
            'Jimmy Kimmel''s Comedy Club',
            '3545 S Las Vegas Blvd',
            'https://jimmykimmelscomedyclub.com',
            'live_nation/KovZ917AOfZ',
            'live_nation',
            true,
            '89109',
            'America/Los_Angeles',
            'Las Vegas',
            'NV',
            'KovZ917AOfZ'
        );
    END IF;
END $$;
