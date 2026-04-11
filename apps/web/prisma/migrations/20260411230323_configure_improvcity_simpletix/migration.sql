-- Update ImprovCity (club 786) metadata — venue is active in Tustin, CA;
-- uses SimpleTix (not SeatEngine); clear stale seatengine_id; fix website to HTTPS;
-- backfill city/state/zip; NULL out scraper until simpletix scraper is built
UPDATE "clubs"
SET
    scraper = NULL,
    scraping_url = 'https://www.simpletix.com/e/improvcity-show-tickets-249393',
    seatengine_id = NULL,
    website = 'https://www.improvcityonline.com',
    city = 'Tustin',
    state = 'CA',
    zip_code = '92780'
WHERE id = 786;
