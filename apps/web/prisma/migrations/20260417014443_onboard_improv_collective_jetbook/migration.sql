-- Onboard The Improv Collective (club 794) to the new JetBook scraper.
--
-- The JetBook scraper was verified to produce 64 live shows from the
-- Bubble.io iframe endpoint at jetbook.co/o_iframe/improv-collective-srzaf.
-- Club metadata (address, city, state, zip, timezone, website, scraping_url)
-- was already set by migration 20260416214532_update_improv_collective_metadata_jetbook.
--
-- This migration:
--   * switches scraper from the stale 'seatengine' placeholder to 'jetbook'
--   * unhides the club so shows appear on the site
UPDATE clubs
SET scraper = 'jetbook',
    visible = TRUE
WHERE id = 794;
