-- Onboard Flipside Theatre (Superior, CO) — TASK-3407
-- (discover-comedy-venues near 80202).
--
-- Flipside Theatre is a dedicated improv / sketch / stand-up comedy theatre at
-- 502 Center Dr, Superior CO. Its entire programming is comedy: improv cabarets,
-- sketch shows, stand-up showcases, open mics, and variety shows. Listings live
-- on the venue's own Squarespace Events collection at /shows.
--
-- Datasource: the venue's own Squarespace Events collection
--   GET https://www.flipsidetheatre.com/api/open/GetItemsByMonth?collectionId=69431f5420e1c432a211723f
-- wired to the generic `squarespace` scraper. The collection is comedy-only, so
-- no title filtering is needed (metadata = {}).
--
-- Verified: make scrape-club-id ID=11300 → "Scraped 25 shows for Flipside Theatre".
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Fixed (visible) venue club.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Flipside Theatre',
       '502 Center Dr M, Superior, CO 80027',
       'https://www.flipsidetheatre.com',
       'Superior', 'CO', '80027', 'America/Denver', 'US', 'club',
       'ChIJ8e_e95Hza4cR_KyAbk--zZs', true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Flipside Theatre');

-- 2. Generic squarespace scraping source (no unique constraint beyond PK, so
--    guard with NOT EXISTS on (club_id, scraper_key)). Comedy-only collection, so
--    no include/exclude title filters.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'squarespace', 'squarespace',
       'https://www.flipsidetheatre.com/api/open/GetItemsByMonth?collectionId=69431f5420e1c432a211723f', 0, true,
       '{}'::jsonb
FROM clubs c
WHERE c.name = 'Flipside Theatre'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'squarespace'
  );
