-- Onboard Counter Weight Brewing (Cheshire, CT)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Counter Weight Brewing') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state, eventbrite_id
        )
        VALUES (
            'Counter Weight Brewing',
            '7 Diana Ct, Cheshire, CT 06410',
            'https://www.counterweightbrewing.com',
            'https://www.eventbrite.com/o/counter-weight-brewing-co-31188770769',
            'eventbrite',
            true,
            '06410',
            'America/New_York',
            'Cheshire',
            'CT',
            '31188770769'
        );
    END IF;
END $$;
