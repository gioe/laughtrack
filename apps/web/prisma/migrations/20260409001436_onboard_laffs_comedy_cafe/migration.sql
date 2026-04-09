-- Onboard Laffs Comedy Cafe (Tucson, AZ)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Laffs Comedy Cafe') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state
        )
        VALUES (
            'Laffs Comedy Cafe',
            '2900 E Broadway Blvd',
            'https://www.laffstucson.com',
            'https://www.laffstucson.com/coming-soon.html',
            'laffs_comedy_cafe',
            true,
            '85716',
            'America/Phoenix',
            'Tucson',
            'AZ'
        );
    END IF;
END $$;
