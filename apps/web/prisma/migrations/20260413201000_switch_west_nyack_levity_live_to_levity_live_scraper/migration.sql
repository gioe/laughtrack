-- Switch West Nyack Levity Live from json_ld to custom levity_live scraper
-- Two-pass scraper captures per-showtime data from comic detail pages
-- (json_ld only sees 1 showtime per event on the calendar page)
UPDATE "clubs"
SET
    scraper = 'levity_live',
    ticketmaster_id = NULL
WHERE id = 26;
