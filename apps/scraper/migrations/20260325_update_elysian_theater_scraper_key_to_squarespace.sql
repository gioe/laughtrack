-- TASK-694: Generalize Squarespace scraper — rename key and embed collectionId in scraping_url
-- Renames the scraper key from 'elysian_theater' to 'squarespace' and updates scraping_url
-- to include the collectionId query param so the generic scraper can read it directly.

UPDATE clubs
SET
    scraper = 'squarespace',
    scraping_url = 'https://www.elysiantheater.com/api/open/GetItemsByMonth?collectionId=613af44feffe2b7f78a46b63'
WHERE name = 'The Elysian Theater'
  AND scraper = 'elysian_theater';
