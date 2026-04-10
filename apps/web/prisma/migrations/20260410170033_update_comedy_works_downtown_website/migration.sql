-- Update Comedy Works Downtown (club 1036) website URL
-- Venue is active at comedyworks.com but had no website stored
UPDATE "clubs"
SET website = 'https://comedyworks.com',
    scraping_url = 'https://comedyworks.com/shows/calendar'
WHERE id = 1036;
