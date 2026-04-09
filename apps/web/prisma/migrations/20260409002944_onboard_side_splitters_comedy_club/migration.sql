-- Onboard Side Splitters Comedy Club (Tampa, FL)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Side Splitters Comedy Club') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state, ovationtix_client_id
        )
        VALUES (
            'Side Splitters Comedy Club',
            '12938 N Dale Mabry Hwy, Tampa, FL 33618',
            'https://sidesplitterscomedy.com',
            'https://web.ovationtix.com/trs/cal/35578',
            'ovationtix',
            true,
            '33618',
            'America/New_York',
            'Tampa',
            'FL',
            '35578'
        );
    END IF;
END $$;
