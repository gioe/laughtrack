ALTER TABLE comedians
  ADD COLUMN IF NOT EXISTS website_health_status VARCHAR,
  ADD COLUMN IF NOT EXISTS website_health_failure_count INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS website_health_checked_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS website_scraping_url_health_status VARCHAR,
  ADD COLUMN IF NOT EXISTS website_scraping_url_health_failure_count INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS website_scraping_url_health_checked_at TIMESTAMPTZ;
