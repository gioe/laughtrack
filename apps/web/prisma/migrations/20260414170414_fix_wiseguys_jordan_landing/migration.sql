-- Fix Wiseguys - Jordan Landing (club 389) — wrong seatengine_id (360→367)
-- Old SeatEngine venue 360 returned 0 events; real venue ID is 367
-- (confirmed from show page HTML at jordanlanding-wiseguyscomedy-com.seatengine.com)
-- Also backfill website, address, city, state, zip, timezone
UPDATE "clubs"
SET
    seatengine_id = '367',
    website = 'https://www.wiseguyscomedy.com/utah/west-jordan',
    address = '3763 West Center Park Dr',
    city = 'West Jordan',
    state = 'UT',
    zip_code = '84084',
    timezone = 'America/Denver',
    scraping_url = 'https://www.wiseguyscomedy.com/utah/west-jordan'
WHERE id = 389;
