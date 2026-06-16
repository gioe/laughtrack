-- Onboard The Auricle - Venue & Bar (Canton, OH) — TASK-2884
--
-- The Auricle is primarily a live-music/variety venue that also hosts a
-- recurring comedy open mic. It runs on Square Online and surfaces its calendar
-- from its Facebook Page via a SociableKit widget backed by a public JSON feed
-- (data.accentapi.com/feed/55840.json). A net-new venue scraper
-- (scraper_key=the_auricle) reads that feed and keeps ONLY comedy events
-- (music/drag/karaoke/etc. are excluded), so the venue contributes only its
-- comedy programming. Verified: 1 comedy show scraped (Comedy Open Mic).
-- Fixed venue → visible=true.
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Auricle - Venue & Bar', '201 Cleveland Ave NW, Canton, OH 44702, USA', 'https://www.theauricle.net/', 'Canton', 'OH', 'America/New_York', 'US', 'club', 'ChIJ45ZmKnrQNogRQnw63k2QPfM', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Auricle - Venue & Bar');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'custom'::"ScrapingPlatform", 'the_auricle', 'https://data.accentapi.com/feed/55840.json', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'The Auricle - Venue & Bar'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'the_auricle');
