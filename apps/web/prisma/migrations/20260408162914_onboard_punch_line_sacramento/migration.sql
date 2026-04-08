-- Onboard Punch Line Sacramento (Sacramento, CA)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Punch Line Sacramento') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state, ticketmaster_id
        )
        VALUES (
            'Punch Line Sacramento',
            '2100 Arden Way, Sacramento, CA 95825',
            'https://www.punchlinesac.com',
            'https://www.punchlinesac.com/shows',
            'live_nation',
            true,
            '95825',
            'America/Los_Angeles',
            'Sacramento',
            'CA',
            'KovZpZAEkFIA'
        );
    END IF;
END $$;
