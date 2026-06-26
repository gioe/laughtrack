-- Onboard Strike Theater (Minneapolis, MN) — TASK-3325
-- (discover-comedy-venues near 55401; Google primary_type=performing_arts_theater).
--
-- Strike Theater is a dedicated improv/sketch/comedy theater — ComedySportz,
-- Improv-A-Go-Go, BALLS Cabaret, Vilification Tennis, Friday Night Improv — with
-- near-100% comedy programming. Its calendar lives on the venue's own Squarespace
-- Events collection at /shows (collectionId 68bf851b23e5e708e760bb9b); all events
-- are at the single Strike Theater venue.
--
-- Datasource: the venue's own Squarespace Events collection
--   GET https://strike.theater/api/open/GetItemsByMonth?collectionId=68bf851b23e5e708e760bb9b
-- wired to the generic `squarespace` scraper. Pure-comedy collection, so no
-- include/exclude title filters are needed.
--
-- Verified: `make scrape-club-id ID=<club_id>` scraped 31 shows.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Fixed (visible) venue club.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Strike Theater',
       '824 NE 18th Ave, Minneapolis, MN 55418',
       'https://strike.theater',
       'Minneapolis', 'MN', '55418', 'America/Chicago', 'US', 'club',
       'ChIJ873W-ZMts1IRJqGNWoNuh00', true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Strike Theater');

-- 2. Generic squarespace scraping source (no unique constraint beyond PK, so
--    guard with NOT EXISTS on (club_id, scraper_key)).
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'squarespace', 'squarespace',
       'https://strike.theater/api/open/GetItemsByMonth?collectionId=68bf851b23e5e708e760bb9b', 0, true,
       '{}'::jsonb
FROM clubs c
WHERE c.name = 'Strike Theater'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'squarespace'
  );
