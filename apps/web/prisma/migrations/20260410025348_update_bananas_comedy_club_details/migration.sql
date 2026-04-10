-- Update Bananas Comedy Club (ID=850): fix dead website (bcccme.com → bananascomedyclub.com),
-- add location, and switch from broken SeatEngine API (venue_id=294 returns 0 shows) to
-- venue-specific white-label scraper that crawls event pages for JSON-LD.
UPDATE "clubs"
SET
    website = 'https://www.bananascomedyclub.com',
    scraping_url = 'https://www.bananascomedyclub.com',
    scraper = 'seatengine_web',
    address = '801 Rutherford Ave, Rutherford, NJ 07070',
    city = 'Rutherford',
    state = 'NJ',
    zip_code = '07070',
    timezone = 'America/New_York'
WHERE id = 850;
