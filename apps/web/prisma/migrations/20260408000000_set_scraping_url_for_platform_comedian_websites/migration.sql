-- Set website_scraping_url = website for comedian websites hosted on
-- platforms with structured event APIs (komi.io, Squarespace, Wix).
-- The ComedianWebsiteScraper queries on website_scraping_url IS NOT NULL,
-- so these comedians are currently excluded from scraping.

UPDATE comedians
SET website_scraping_url = website
WHERE website_scraping_url IS NULL
  AND website IS NOT NULL
  AND website <> ''
  AND (
    website ILIKE '%.komi.io%'
    OR website ILIKE '%.squarespace.com%'
    OR website ILIKE '%.wixsite.com%'
  );
