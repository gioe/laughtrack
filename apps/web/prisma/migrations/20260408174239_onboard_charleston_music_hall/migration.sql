-- Onboard Charleston Music Hall (Charleston, SC)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Charleston Music Hall') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state, ticketmaster_id
        )
        VALUES (
            'Charleston Music Hall',
            '37 John St, Charleston, SC 29403',
            'https://charlestonmusichall.com',
            'https://charlestonmusichall.com/calendar/',
            'live_nation',
            true,
            '29403',
            'America/New_York',
            'Charleston',
            'SC',
            'KovZpZA1vt6A'
        );
    END IF;
END $$;
