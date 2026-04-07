-- Add Tacoma Comedy Club - Downtown (Tacoma, WA) and update existing
-- Tacoma Comedy Club scraping URL to filter by location label.
-- Both locations share tacomacomedyclub.com/events; the #location=
-- fragment is used by the seatengine_classic scraper to filter shows
-- by their event-label text.

DO $$
BEGIN
    -- Add the Downtown location
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Tacoma Comedy Club - Downtown') THEN
        INSERT INTO "clubs" (name, address, website, scraping_url, scraper, seatengine_id, visible, zip_code, phone_number, popularity, timezone, city, state)
        VALUES ('Tacoma Comedy Club - Downtown', '933 Market St, Tacoma, WA 98402', 'https://www.tacomacomedyclub.com', 'https://www.tacomacomedyclub.com/events#location=Downtown', 'seatengine_classic', '157', true, '98402', '(253) 282-7203', 0, 'America/Los_Angeles', 'Tacoma', 'WA');
    END IF;

    -- Update the existing 6th Ave location to filter by its label
    UPDATE "clubs"
    SET scraping_url = 'https://www.tacomacomedyclub.com/events#location=6th and Proctor',
        website = 'https://www.tacomacomedyclub.com'
    WHERE name = 'Tacoma Comedy Club'
      AND scraping_url NOT LIKE '%#location=%';
END $$;
