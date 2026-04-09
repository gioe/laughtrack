-- Onboard Skyline Comedy Club (Appleton, WI)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Skyline Comedy Club') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state, seatengine_id
        )
        VALUES (
            'Skyline Comedy Club',
            '1004 S Olde Oneida St, 3rd floor',
            'https://www.skylinecomedy.com',
            'www-skylinecomedy-com.seatengine.com/events',
            'seatengine_classic',
            true,
            '54915',
            'America/Chicago',
            'Appleton',
            'WI',
            '299'
        );
    END IF;
END $$;
