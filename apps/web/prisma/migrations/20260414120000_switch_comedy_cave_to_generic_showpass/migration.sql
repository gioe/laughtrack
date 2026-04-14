-- Switch Comedy Cave (club 818) from venue-specific comedy_cave scraper
-- to the generic showpass scraper. The scraping_url now stores the Showpass
-- calendar API base URL so the generic scraper can extract the venue slug.
UPDATE clubs
SET
    scraper      = 'showpass',
    scraping_url = 'https://www.showpass.com/api/public/venues/comedy-cave/calendar/'
WHERE id = 818;
