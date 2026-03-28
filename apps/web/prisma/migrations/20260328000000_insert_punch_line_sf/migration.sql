-- Insert Punch Line Comedy Club - San Francisco, discovered during TASK-747 venue onboarding.
-- Ticketmaster Discovery API venue ID: KovZpZAE6e7A
-- Address: 444 Battery Street, San Francisco, CA 94111

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Punch Line Comedy Club - San Francisco') THEN
        INSERT INTO "clubs" (name, address, website, scraping_url, scraper, visible, zip_code, phone_number, popularity, timezone, city, state, ticketmaster_id)
        VALUES ('Punch Line Comedy Club - San Francisco', '444 Battery Street', 'https://www.punchlinecomedyclub.com', 'ticketmaster/KovZpZAE6e7A', 'live_nation', true, '94111', NULL, 0, 'America/Los_Angeles', 'San Francisco', 'CA', 'KovZpZAE6e7A');
    END IF;
END $$;
