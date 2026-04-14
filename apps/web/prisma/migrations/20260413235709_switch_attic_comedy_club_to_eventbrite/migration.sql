-- Switch The Attic Comedy Club (ID=575) from SeatEngine to Eventbrite
-- SeatEngine venue 555 returns 404; club now sells tickets via Eventbrite organizer 113948356841
-- Also backfill address, city, state, zip_code, and timezone

UPDATE "clubs"
SET
    scraper = 'eventbrite',
    eventbrite_id = '113948356841',
    seatengine_id = NULL,
    scraping_url = 'https://www.eventbrite.com/o/the-attic-comedy-club-113948356841',
    address = '892 Oak Street',
    city = 'Columbus',
    state = 'OH',
    zip_code = '43205',
    timezone = 'America/New_York'
WHERE id = 575;
