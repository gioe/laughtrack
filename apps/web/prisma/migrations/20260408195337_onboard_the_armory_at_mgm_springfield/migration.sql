-- Onboard The Armory at MGM Springfield (Springfield, MA)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'The Armory at MGM Springfield') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state, ticketmaster_id
        )
        VALUES (
            'The Armory at MGM Springfield',
            'One MGM Way',
            'https://roarcomedyclub.com',
            'https://roarcomedyclub.com',
            'live_nation',
            true,
            '01103',
            'America/New_York',
            'Springfield',
            'MA',
            'KovZ917ALxH'
        );
    END IF;
END $$;
