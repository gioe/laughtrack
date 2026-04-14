-- Switch The Backline (club 796) from SeatEngine to Crowdwork
-- SeatEngine venue 217 returns 404; club now uses Crowdwork (slug: thebacklinecomedytheatre)
-- Backfill address, city, state, zip, timezone

UPDATE "clubs"
SET
    scraper         = 'the_backline',
    scraping_url    = 'https://crowdwork.com/api/v2/thebacklinecomedytheatre/shows',
    website         = 'https://www.backlinecomedy.com',
    address         = '1618 Harney St, Omaha, NE 68102',
    city            = 'Omaha',
    state           = 'NE',
    zip_code        = '68102',
    timezone        = 'America/Chicago',
    seatengine_id   = NULL
WHERE id = 796;
