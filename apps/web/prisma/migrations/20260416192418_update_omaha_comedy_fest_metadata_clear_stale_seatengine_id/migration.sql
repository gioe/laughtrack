-- Update Omaha Comedy Fest (club 784, formerly "Omaha Improv Festival (Shows)") metadata.
-- Festival rebranded: old domain omahaimprovfest.com → new omahacomedyfest.com.
-- Old seatengine_id=193 is stale; the tickets page now hand-links to 5 different
-- per-event platforms (Crowdwork, exploretock, Don't Tell Comedy, Next Stop Comedy,
-- Humanitix) with no unified API. Improv shows hosted at The Backline (club 796)
-- are already captured by that venue's scraper. Keeping visible=false.
UPDATE clubs
SET
    name = 'Omaha Comedy Fest',
    website = 'https://www.omahacomedyfest.com',
    scraping_url = 'https://www.omahacomedyfest.com',
    city = 'Omaha',
    state = 'NE',
    country = 'US',
    timezone = 'America/Chicago',
    seatengine_id = NULL,
    scraper = NULL
WHERE id = 784;
