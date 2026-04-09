-- Onboard Comedy Club Haug (Rotterdam, Netherlands)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Comedy Club Haug') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, timezone, city, state
        )
        VALUES (
            'Comedy Club Haug',
            'Boompjeskade 11, 3011 XE Rotterdam, Netherlands',
            'https://comedyclubhaug.com',
            'https://comedyclubhaug.com/shows',
            'comedy_club_haug',
            true,
            'Europe/Amsterdam',
            'Rotterdam',
            'Netherlands'
        );
    END IF;
END $$;
