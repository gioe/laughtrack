-- Insert McCurdy's Comedy Theatre (Sarasota, FL), discovered via Bandsintown tour dates (TASK-1006).
-- Custom ColdFusion website with shows listed at mccurdyscomedy.com/shows/.
-- Tickets sold through Etix (buy.cfm redirects to etix.com/ticket/p/<id>).

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'McCurdy''s Comedy Theatre') THEN
        INSERT INTO "clubs" (name, address, website, scraping_url, scraper, visible, zip_code, phone_number, popularity, timezone, city, state)
        VALUES ('McCurdy''s Comedy Theatre', '1923 Ringling Blvd, Sarasota, FL 34236', 'https://www.mccurdyscomedy.com', 'https://www.mccurdyscomedy.com/shows/', 'mccurdys_comedy_theatre', true, '34236', '941-925-3869', 0, 'America/New_York', 'Sarasota', 'FL');
    END IF;
END $$;
