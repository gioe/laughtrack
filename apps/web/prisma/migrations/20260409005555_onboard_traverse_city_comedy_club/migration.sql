-- Onboard Traverse City Comedy Club (Traverse City, MI)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Traverse City Comedy Club') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state
        )
        VALUES (
            'Traverse City Comedy Club',
            '738 South Garfield Avenue, Traverse City, MI 49686',
            'https://traversecitycomedyclub.com',
            'https://mynorthtickets.com/organizations/traverse-city-comedy-club',
            'json_ld',
            true,
            '49686',
            'America/Detroit',
            'Traverse City',
            'MI'
        );
    END IF;
END $$;
