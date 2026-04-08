-- Switch Clint's Comedy Club from eventbrite to wix_events scraper
-- The venue uses Wix Events for individual show listings; the Eventbrite
-- organizer page only has a single year-long placeholder event.
UPDATE "clubs"
SET scraper = 'wix_events',
    scraping_url = 'https://www.clintscomedyclub.com',
    wix_comp_id = 'comp-m333exmt',
    eventbrite_id = NULL
WHERE name = 'Clint''s Comedy Club';
