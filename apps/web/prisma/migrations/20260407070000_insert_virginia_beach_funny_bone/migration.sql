-- Insert Virginia Beach Funny Bone Comedy Club
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Virginia Beach Funny Bone') THEN
        INSERT INTO "clubs" (name, address, website, scraping_url, scraper, visible, zip_code, phone_number, popularity, timezone, city, state)
        VALUES (
            'Virginia Beach Funny Bone',
            '4554 Virginia Beach Blvd Suite 100, Virginia Beach, VA 23462',
            'https://vb.funnybone.com',
            'https://vb.funnybone.com/shows/',
            'funny_bone',
            true,
            '23462',
            '(757) 213-5555',
            0,
            'America/New_York',
            'Virginia Beach',
            'VA'
        );
    END IF;
END $$;
