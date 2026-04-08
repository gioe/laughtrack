-- Onboard Largo at the Coronet (Los Angeles, CA)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Largo at the Coronet') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state
        )
        VALUES (
            'Largo at the Coronet',
            '366 N La Cienega Blvd, Los Angeles, CA 90048',
            'https://largo-la.com',
            'https://largo-la.com/',
            'largo_at_the_coronet',
            true,
            '90048',
            'America/Los_Angeles',
            'Los Angeles',
            'CA'
        );
    END IF;
END $$;
