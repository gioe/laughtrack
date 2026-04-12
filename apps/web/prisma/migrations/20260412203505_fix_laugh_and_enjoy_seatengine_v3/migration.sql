-- Fix Laugh And Enjoy (club 602): migrate from seatengine to seatengine_v3
-- Old seatengine_id 586 returns HTTP 401; venue now uses SeatEngine v3 GraphQL API
-- Venue UUID: c91f790c-4cb1-41cd-84fc-bee3b91a0b61
-- Also backfill missing location data (West Chicago, IL)
UPDATE "clubs"
SET
    scraper = 'seatengine_v3',
    seatengine_id = 'c91f790c-4cb1-41cd-84fc-bee3b91a0b61',
    address = '2005 Franciscan Way',
    city = 'West Chicago',
    state = 'IL',
    zip_code = '60185',
    timezone = 'America/Chicago'
WHERE id = 602;
