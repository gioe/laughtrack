-- Onboard The Lost Church (San Francisco, CA)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'The Lost Church') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state
        )
        VALUES (
            'The Lost Church',
            '988 Columbus Avenue, San Francisco, CA 94133',
            'https://thelostchurch.org',
            'https://thelostchurch.my.salesforce-sites.com/ticket',
            'lost_church',
            true,
            '94133',
            'America/Los_Angeles',
            'San Francisco',
            'CA'
        );
    END IF;
END $$;
