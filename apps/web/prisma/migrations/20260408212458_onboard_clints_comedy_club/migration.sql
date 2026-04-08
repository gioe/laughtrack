-- Onboard Clint's Comedy Club (Overland Park, KS)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Clint''s Comedy Club') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state, eventbrite_id
        )
        VALUES (
            'Clint''s Comedy Club',
            '7332 W 119th St, Overland Park, KS 66213',
            'https://www.clintscomedyclub.com',
            'https://www.eventbrite.com/o/clints-comedy-club-17805987484',
            'eventbrite',
            true,
            '66213',
            'America/Chicago',
            'Overland Park',
            'KS',
            '17805987484'
        );
    END IF;
END $$;
