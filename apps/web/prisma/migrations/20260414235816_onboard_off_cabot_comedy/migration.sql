-- Onboard Off Cabot Comedy and Events (Beverly, MA)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Off Cabot Comedy and Events') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state
        )
        VALUES (
            'Off Cabot Comedy and Events',
            '9 Wallis St, Beverly, MA 01915',
            'https://thecabot.org/offcabot/',
            'https://thecabot.org/offcabot/',
            'off_cabot',
            true,
            '01915',
            'America/New_York',
            'Beverly',
            'MA'
        );
    END IF;
END $$;
