-- TASK-1692: route Etix through the same residential-proxy mechanism used for Tixr,
-- and switch House of Comedy Bloomington to a direct venue-page scraper so it no
-- longer depends on DataDome-blocked Tixr event pages.

INSERT INTO scrapers (key, use_residential_proxy, notes, updated_at)
VALUES ('etix', true, 'Etix venue listing pages return DataDome 403 blocks from direct egress', CURRENT_TIMESTAMP)
ON CONFLICT (key) DO UPDATE
SET use_residential_proxy = EXCLUDED.use_residential_proxy,
    notes = EXCLUDED.notes,
    updated_at = CURRENT_TIMESTAMP;

UPDATE scraping_sources
SET scraper_key = 'house_of_comedy_bloomington',
    updated_at = CURRENT_TIMESTAMP
WHERE club_id = 655
  AND platform = 'tixr'
  AND enabled = true;
