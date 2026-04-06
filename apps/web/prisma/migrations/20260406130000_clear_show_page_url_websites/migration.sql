-- Clear website field on comedian records where the URL is a show/event page,
-- not the comedian's own website. These pollute the comedian_websites scraper
-- by wasting HTTP requests on venue ticketing pages.
UPDATE comedians
SET website = NULL,
    website_discovery_source = NULL,
    website_last_scraped = NULL,
    website_scrape_strategy = NULL
WHERE website IS NOT NULL
  AND (
    website ~ '/shows/[0-9]+'
    OR website ~ '/events/[0-9]+'
    OR website ~ '/checkout/'
    OR website ~ '/tickets/'
    OR website ~ '/e/[0-9]+'
    OR website ~ '/event/'
  );
