-- Onboard The Moore Theatre (Seattle, WA)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'The Moore Theatre') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state, ticketmaster_id
        )
        VALUES (
            'The Moore Theatre',
            '1932 2nd Ave, Seattle, WA 98101',
            'https://www.stgpresents.org/stg-venues/moore-theatre/',
            'https://www.stgpresents.org/stg-venues/moore-theatre/events/',
            'live_nation',
            true,
            '98101',
            'America/Los_Angeles',
            'Seattle',
            'WA',
            'KovZpZA1vFJA'
        );
    END IF;
END $$;
