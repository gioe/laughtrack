-- Onboard The Moon (Tallahassee, FL)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'The Moon') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state
        )
        VALUES (
            'The Moon',
            '1105 E Lafayette St',
            'https://moonevents.com',
            'https://moonevents.com/events/',
            'the_moon',
            true,
            '32301',
            'America/New_York',
            'Tallahassee',
            'FL'
        );
    END IF;
END $$;
