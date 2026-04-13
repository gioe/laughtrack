-- Switch Post Office Cafe & Cabaret (club 223) from seatengine to ThunderTix scraper
-- Venue is active in Provincetown, MA; SeatEngine venue 20 returns 404;
-- ThunderTix at postofficecafecabaret.thundertix.com has 147 upcoming performances.
-- Also fixes website URL (was postofficecabaret.com, now postofficecafe.net)
-- and fills in missing address/city/state/timezone.
UPDATE "clubs"
SET
    scraper = 'post_office_cafe',
    scraping_url = 'https://postofficecafecabaret.thundertix.com',
    website = 'https://www.postofficecafe.net/',
    address = '303 Commercial St',
    city = 'Provincetown',
    state = 'MA',
    zip_code = '02657',
    timezone = 'America/New_York',
    seatengine_id = NULL
WHERE id = 223;
