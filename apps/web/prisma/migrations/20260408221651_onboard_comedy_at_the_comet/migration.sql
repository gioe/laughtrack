-- Onboard Comedy At The Comet (Cincinnati, OH)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Comedy At The Comet') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state, eventbrite_id
        )
        VALUES (
            'Comedy At The Comet',
            '4579 Hamilton Avenue',
            'https://www.bombsawaycomedy.com',
            'https://www.eventbrite.com/o/bombs-away-comedy-18372505544',
            'eventbrite',
            true,
            '45223',
            'America/New_York',
            'Cincinnati',
            'OH',
            '18372505544'
        );
    END IF;
END $$;
