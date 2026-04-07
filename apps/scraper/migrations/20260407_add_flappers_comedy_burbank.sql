-- Add Flappers Comedy Club And Restaurant Burbank (Burbank, CA)
-- Discovered via Bandsintown tour dates for JR De Guzman and Jeff Allen.
-- Bandsintown venue ID: 10018298
-- Uses tour_dates scraper (comedian-centric — shows discovered via artist Bandsintown IDs).

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Flappers Comedy Club And Restaurant Burbank') THEN
        INSERT INTO "clubs" (name, address, website, scraping_url, scraper, visible, zip_code, phone_number, popularity, timezone, city, state)
        VALUES (
            'Flappers Comedy Club And Restaurant Burbank',
            '102 E Magnolia Blvd, Burbank, CA 91502',
            'https://flapperscomedy.com',
            'tour_dates',
            'tour_dates',
            true,
            '91502',
            '(818) 845-9721',
            0,
            'America/Los_Angeles',
            'Burbank',
            'CA'
        );
    END IF;
END $$;
