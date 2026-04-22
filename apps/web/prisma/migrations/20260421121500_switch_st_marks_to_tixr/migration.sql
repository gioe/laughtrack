-- Switch St. Marks Comedy Club (club 16) from the specialized st_marks scraper
-- to the shared tixr scraper.
--
-- Use the public website as scraping_url because the current page exposes live
-- Tixr event links directly, so the generic scraper can benefit immediately
-- once Tixr/DataDome fetch reliability is improved.
UPDATE clubs
SET
    scraper = 'tixr',
    scraping_url = 'https://www.stmarkscomedyclub.com'
WHERE id = 16
  AND name = 'St. Marks Comedy Club'
  AND scraper = 'st_marks';
