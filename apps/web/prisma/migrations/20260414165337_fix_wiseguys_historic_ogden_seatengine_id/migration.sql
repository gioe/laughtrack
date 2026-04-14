-- Fix Wiseguys - Historic Ogden (club 391): correct seatengine_id from 362 to 366,
-- update website/metadata. Old SeatEngine venue 362 returned 0 events; real venue ID
-- is 366 (confirmed from show page HTML). Also backfill address/city/state/zip/timezone.
UPDATE "clubs"
SET
    seatengine_id = '366',
    website = 'https://www.wiseguyscomedy.com/utah/ogden',
    scraping_url = 'https://www.wiseguyscomedy.com/utah/ogden',
    address = '269 Historic 25th St',
    city = 'Ogden',
    state = 'UT',
    zip_code = '84401',
    timezone = 'America/Denver'
WHERE id = 391;
