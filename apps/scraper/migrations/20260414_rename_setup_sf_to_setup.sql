-- Rename scraper key from 'setup_sf' to 'setup' for all Setup locations.
-- The scraper is now city-agnostic — each club's scraping_url encodes the
-- city-specific Google Sheet gid. No code changes needed to add new cities.

UPDATE clubs
SET scraper = 'setup'
WHERE scraper = 'setup_sf';
