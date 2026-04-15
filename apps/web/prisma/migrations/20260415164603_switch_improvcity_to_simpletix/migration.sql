-- Switch ImprovCity (club 786) from seatengine to simpletix scraper
-- and set timezone for Tustin, CA
UPDATE clubs
SET scraper = 'simpletix',
    timezone = 'America/Los_Angeles',
    seatengine_id = NULL
WHERE id = 786;
