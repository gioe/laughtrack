-- Update Mesquite St. Comedy Club (club 837) metadata from adopt-scraper research.
-- Bulk-imported from SeatEngine on 2026-04-06 with seatengine_id=279 and 0 shows —
-- that ID is invalid. Real platform is TicketLeap (events.ticketleap.com/events/funny,
-- org slug "funny"). Official website is www.mesquitestreet.com (Wix); the previously
-- stored laughdowntown.com URL no longer resolves. The TicketLeap org carries 7
-- upcoming shows (e.g., Craig Conant, David Koechner, Steve-O) — venue is active.
--
-- No existing TicketLeap scraper in the codebase; a new Path B scraper must be built
-- before visible can flip to true. Keeping visible=false and scraper='seatengine' as
-- placeholder (will be swapped to 'ticketleap' in the scraper-build task). Storing the
-- correct TicketLeap listing URL in scraping_url so the follow-up task inherits it.
UPDATE clubs
SET address = '617 Mesquite Street',
    city = 'Corpus Christi',
    state = 'TX',
    zip_code = '78401',
    timezone = 'America/Chicago',
    website = 'https://www.mesquitestreet.com',
    scraping_url = 'https://events.ticketleap.com/events/funny'
WHERE id = 837;
