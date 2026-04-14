-- Onboard Kellar's: Modern Magic and Comedy Club (Erie, PA)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Kellar''s: Modern Magic and Comedy Club') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state
        )
        VALUES (
            'Kellar''s: Modern Magic and Comedy Club',
            '1402 State St',
            'https://kellarsmagic.com',
            'https://kellarsmagic.com/tc-events/',
            'kellars',
            true,
            '16501',
            'America/New_York',
            'Erie',
            'PA'
        );
    END IF;
END $$;
