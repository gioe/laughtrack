-- Insert Helium Comedy Club - Indianapolis, discovered during TASK-494 venue discovery.
-- Ticketmaster Discovery API venue ID: Z7r9jZa7cb

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Helium Comedy Club - Indianapolis') THEN
        INSERT INTO "clubs" (name, address, website, scraping_url, scraper, visible, zip_code, phone_number, popularity, timezone, city, state, ticketmaster_id)
        VALUES ('Helium Comedy Club - Indianapolis', '', '', 'ticketmaster/Z7r9jZa7cb', 'live_nation', true, NULL, NULL, 0, 'America/Indiana/Indianapolis', 'Indianapolis', 'IN', 'Z7r9jZa7cb');
    END IF;
END $$;
