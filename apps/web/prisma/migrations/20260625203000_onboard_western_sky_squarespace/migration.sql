-- Onboard Western Sky Bar & Taproom (Englewood, CO) — TASK-3405
-- (discover-comedy-venues near 80202, 7.7 mi).
--
-- Western Sky is a South Broadway bar / taproom. Its calendar is mostly karaoke,
-- trivia, live music, book club, run club, and maker markets, but it ALSO runs
-- genuine recurring stand-up comedy on its own Squarespace Events collection:
-- the weekly "South South Broadway Sunday Open Mic" (comics/musicians/poets) and
-- the recurring "Goblin Mode Improv" live-comedy show (plus a monthly "Weenie
-- Roast: Comedy Roast Battle").
--
-- Datasource: the venue's own Squarespace Events collection
--   GET https://www.westernskybar.com/api/open/GetItemsByMonth?collectionId=61d34d566f547e2498c25420
-- wired to the generic `squarespace` scraper. Because the collection is mixed-use,
-- metadata.include_title_patterns isolates the comedy and drops karaoke / trivia /
-- live music / book club / markets (Lion's Lair / Cloverdale precedent, TASK-3401 / TASK-3236).
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Fixed (visible) venue club.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Western Sky Bar & Taproom',
       '4361 S Broadway',
       'https://www.westernskybar.com',
       'Englewood', 'CO', '80113', 'America/Denver', 'US', 'club',
       'ChIJXeTJ4leBbIcRTP9Y8l5uVmY', true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Western Sky Bar & Taproom');

-- 2. Generic squarespace scraping source (no unique constraint beyond PK, so
--    guard with NOT EXISTS on (club_id, scraper_key)). include_title_patterns
--    keeps only the comedy on this mixed-use Events collection.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'squarespace', 'squarespace',
       'https://www.westernskybar.com/api/open/GetItemsByMonth?collectionId=61d34d566f547e2498c25420', 0, true,
       '{"include_title_patterns": ["comedy", "roast", "improv", "stand[ -]?up", "open mic"]}'::jsonb
FROM clubs c
WHERE c.name = 'Western Sky Bar & Taproom'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'squarespace'
  );
