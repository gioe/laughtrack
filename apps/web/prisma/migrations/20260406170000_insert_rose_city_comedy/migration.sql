-- Insert Rose City Comedy (Tyler, TX), discovered via Bandsintown tour dates (TASK-1003).
-- Uses Tixr for ticketing; venue website embeds tixr.com event links directly.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Rose City Comedy') THEN
        INSERT INTO "clubs" (name, address, website, scraping_url, scraper, visible, zip_code, phone_number, popularity, timezone, city, state)
        VALUES ('Rose City Comedy', '7428 Old Jacksonville Hwy, Suite 10, Tyler, TX 75703', 'https://rosecitycomedy.club', 'https://rosecitycomedy.club', 'tixr', true, '75703', NULL, 0, 'America/Chicago', 'Tyler', 'TX');
    END IF;
END $$;
