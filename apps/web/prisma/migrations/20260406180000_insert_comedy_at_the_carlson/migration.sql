-- Insert Comedy @ The Carlson (Rochester, NY), discovered via Bandsintown tour dates (TASK-1004).
-- Uses OvationTix for ticketing (client ID 35843). Production IDs discovered from
-- OvationTix calendar page at web.ovationtix.com/trs/cal/35843.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Comedy @ The Carlson') THEN
        INSERT INTO "clubs" (name, address, website, scraping_url, scraper, visible, zip_code, phone_number, popularity, timezone, city, state)
        VALUES ('Comedy @ The Carlson', '50 Carlson Rd, Rochester, NY 14610', 'https://www.carlsoncomedy.com', 'https://web.ovationtix.com/trs/cal/35843', 'comedy_at_the_carlson', true, '14610', '585-426-6339', 0, 'America/New_York', 'Rochester', 'NY');
    END IF;
END $$;
