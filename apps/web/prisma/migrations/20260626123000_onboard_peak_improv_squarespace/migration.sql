-- Onboard Peak Improv Theater (Colorado Springs, CO) — TASK-3440
-- (discover-comedy-venues near 80202, 61.2 mi; Google primary_type=comedy_club).
--
-- Peak Improv is a dedicated improv/comedy theater: improv shows, sketch, musical
-- improv, puppet improv, free improv jams, plus stand-up. Its calendar is hosted
-- on the venue's own Squarespace Events collection "Shows & Events".
--
-- Datasource: the venue's own Squarespace Events collection
--   GET https://peakimprov.com/api/open/GetItemsByMonth?collectionId=6553f7941c7f842a75cbfd87
-- wired to the generic `squarespace` scraper. The collection is pure-comedy
-- (a dedicated improv theater), so no include/exclude title filters are needed.
--
-- Verified: `make scrape-club-id ID=<club_id>` scraped 49 shows.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Fixed (visible) venue club.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Peak Improv Theater',
       '3440 N Carefree Cir Ste 140-150, Colorado Springs, CO 80917, USA',
       'https://peakimprov.com/',
       'Colorado Springs', 'CO', '80917', 'America/Denver', 'US', 'club',
       'ChIJta10EbZPE4cRQ6qsGIgssn0', true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Peak Improv Theater');

-- 2. Generic squarespace scraping source (no unique constraint beyond PK, so
--    guard with NOT EXISTS on (club_id, scraper_key)).
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'squarespace', 'squarespace',
       'https://peakimprov.com/api/open/GetItemsByMonth?collectionId=6553f7941c7f842a75cbfd87', 0, true,
       '{}'::jsonb
FROM clubs c
WHERE c.name = 'Peak Improv Theater'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'squarespace'
  );
