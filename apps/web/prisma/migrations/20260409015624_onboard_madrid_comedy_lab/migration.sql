-- Onboard Madrid Comedy Lab (Madrid, Spain)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Madrid Comedy Lab') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, timezone, city
        )
        VALUES (
            'Madrid Comedy Lab',
            'Calle del Amor de Dios 13, 28014 Madrid, Spain',
            'https://www.madridcomedylab.com',
            'https://fienta.com/api/v1/public/events?organizer=24814',
            'madrid_comedy_lab',
            true,
            'Europe/Madrid',
            'Madrid'
        );
    END IF;
END $$;
