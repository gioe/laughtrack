-- Switch Comedy Cellar New York from email scraper to web scraper.
-- The comedy_cellar web scraper uses Comedy Cellar's internal WordPress API
-- and does not require GMAIL_REFRESH_TOKEN.
UPDATE clubs
SET scraper = 'comedy_cellar',
    scraping_url = 'https://www.comedycellar.com/lineup/api/'
WHERE scraper = 'comedy_cellar_email';

-- Switch Gotham Comedy Club from email scraper to web scraper.
-- The gotham web scraper uses Gotham's S3 JSON bucket and does not require
-- GMAIL_REFRESH_TOKEN.
UPDATE clubs
SET scraper = 'gotham',
    scraping_url = 'https://gothamevents.s3.amazonaws.com/events/month/'
WHERE scraper = 'gotham_email';
