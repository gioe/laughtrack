-- Fix Comedy on State scraping_url to point to /events/ page
-- Homepage yields ~8 shows; /events/ page has 28 events with full JSON-LD markup
UPDATE clubs
SET scraping_url = 'https://www.madisoncomedy.com/events/'
WHERE id = 435;
