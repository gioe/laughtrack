-- Onboard Gramercy Theatre (New York City, NY)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Gramercy Theatre') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state, ticketmaster_id
        )
        VALUES (
            'Gramercy Theatre',
            '127 East 23rd Street',
            'https://www.thegramercytheatre.com',
            'https://www.thegramercytheatre.com/shows',
            'live_nation',
            true,
            '10010',
            'America/New_York',
            'New York City',
            'NY',
            'KovZpZAEAdaA'
        );
    END IF;
END $$;
