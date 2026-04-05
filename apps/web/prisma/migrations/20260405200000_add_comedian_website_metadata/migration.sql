-- Add website scraping metadata columns to comedians table
ALTER TABLE "comedians"
  ADD COLUMN "website_discovery_source" VARCHAR,
  ADD COLUMN "website_last_scraped" TIMESTAMPTZ,
  ADD COLUMN "website_scrape_strategy" VARCHAR;
