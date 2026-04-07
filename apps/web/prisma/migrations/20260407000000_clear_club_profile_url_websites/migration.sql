-- Clear website field on comedian records where the URL is a club or directory
-- profile page (e.g., /comedians/<name>, /comedian/<name>, /people/<name>),
-- not the comedian's own website. These pollute the comedian_websites scraper
-- by wasting HTTP requests on venue roster pages that never yield tour dates.
UPDATE comedians
SET website = NULL,
    website_scraping_url = NULL,
    website_discovery_source = NULL,
    website_last_scraped = NULL,
    website_scrape_strategy = NULL
WHERE website IS NOT NULL
  AND (
    website ~ '/comedians/.+'
    OR website ~ '/comedian/.+'
    OR website ~ '/people/.+'
  );
