-- Onboard Lion's Lair (Denver, CO) — TASK-3401
-- (discover-comedy-venues near 80202).
--
-- Lion's Lair is a longtime East Colfax dive / live-music bar. Its calendar is
-- mostly bands, DJ sets, karaoke, and burlesque, but it ALSO runs a genuine
-- recurring weekly stand-up series, "Open Mic Comedy Night Hosted by Anthony
-- Crawford" (every Tuesday), listed on its own Squarespace Events collection.
--
-- Datasource: the venue's own Squarespace Events collection
--   GET https://www.lionslairco.com/api/open/GetItemsByMonth?collectionId=66fb6c12bfea4c2a63d47c4d
-- wired to the generic `squarespace` scraper. Because the collection is mixed-use,
-- metadata.include_title_patterns isolates the comedy night and drops the music
-- open mic / DJs / Gong Show / burlesque (Cloverdale/Clayton precedent, TASK-3236).
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Fixed (visible) venue club.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Lion''s Lair',
       '2022 E Colfax Ave',
       'https://www.lionslairco.com',
       'Denver', 'CO', '80206', 'America/Denver', 'US', 'club',
       'ChIJCZbXnsp-bIcRi00y7JZF8bg', true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Lion''s Lair');

-- 2. Generic squarespace scraping source (no unique constraint beyond PK, so
--    guard with NOT EXISTS on (club_id, scraper_key)). include_title_patterns
--    keeps only the comedy night on this mixed-use Events collection.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'squarespace', 'squarespace',
       'https://www.lionslairco.com/api/open/GetItemsByMonth?collectionId=66fb6c12bfea4c2a63d47c4d', 0, true,
       '{"include_title_patterns": ["comedy", "stand[- ]?up", "comedian"]}'::jsonb
FROM clubs c
WHERE c.name = 'Lion''s Lair'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'squarespace'
  );
