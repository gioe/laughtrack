-- Onboard Dade County Comedy (Miami, FL) — TASK-3347
-- (discover-comedy-venues near 33130, 3.0 mi; Google primary_type=comedy_club).
--
-- Dade County Comedy is a Miami comedy PRODUCER running recurring stand-up shows
-- at many different venues (South Beach Brewing Company, Thorn, Lost City Brewing,
-- Garin, Eddie's Place, etc.). Its show calendar lives on the brand's own
-- Squarespace Events collection "Shows & Events" (/miami-comedy-shows).
--
-- Datasource: the brand's own Squarespace Events collection
--   GET https://www.dadecountycomedy.com/api/open/GetItemsByMonth?collectionId=61d77031f9cb0a62df15aba2
-- wired to the generic `squarespace` scraper. The collection is pure-comedy, so no
-- include/exclude title filters are needed.
--
-- Visibility note: although the producer stages shows at varying venues, the
-- `squarespace` scraper has no per-event venue routing (it assigns every event to
-- the configured club), so this is onboarded as a single visible club — matching
-- every existing squarespace config — so the shows actually surface. A hidden proxy
-- would bury them, since no per-venue clubs are auto-created by this scraper.
--
-- Verified: `make scrape-club-id ID=<club_id>` scraped 19 shows.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Producer club (visible; single club because the squarespace scraper does not
--    route per-venue).
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Dade County Comedy',
       '2809 Bird Ave, Miami, FL 33133',
       'https://www.dadecountycomedy.com',
       'Miami', 'FL', '33133', 'America/New_York', 'US', 'club',
       'ChIJQ2F4VhS_2YgRMBlzlruLP8w', true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Dade County Comedy');

-- 2. Generic squarespace scraping source (no unique constraint beyond PK, so
--    guard with NOT EXISTS on (club_id, scraper_key)).
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'squarespace', 'squarespace',
       'https://www.dadecountycomedy.com/api/open/GetItemsByMonth?collectionId=61d77031f9cb0a62df15aba2', 0, true,
       '{}'::jsonb
FROM clubs c
WHERE c.name = 'Dade County Comedy'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'squarespace'
  );
