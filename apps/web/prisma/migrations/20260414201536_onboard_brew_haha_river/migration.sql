-- Onboard Brew HaHa Comedy at River (Wethersfield, CT)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Brew HaHa Comedy at River') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state, country
        )
        VALUES (
            'Brew HaHa Comedy at River',
            '100 Great Meadow Rd, Wethersfield, CT 06109',
            'https://comedycraftbeer.com',
            'https://comedycraftbeer.com/calendar',
            'brew_haha_river',
            true,
            '06109',
            'America/New_York',
            'Wethersfield',
            'CT',
            'US'
        );
    END IF;
END $$;
