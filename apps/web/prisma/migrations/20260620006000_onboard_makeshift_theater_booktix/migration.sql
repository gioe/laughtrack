-- Onboard Makeshift Theater Akron (Akron, OH) — TASK-2922
--
-- Makeshift Theater (732 W Exchange St, Akron OH 44302; makeshiftakron.org) is a
-- nonprofit theater company at the Coach House that hosts comedy/improv (Point of
-- No Return Improv Comedy) alongside plays. Fixed venue → visible=TRUE.
--
-- Datasource: BookTix box office (makeshift.booktix.com). The box office home
-- (/dept/main) lists each production by code; each production page is
-- server-rendered HTML with one or more showtimes — handled by the NEW generic
-- `booktix` scraper (no native Squarespace Events collection and no JSON-LD, so
-- the squarespace/json_ld scrapers do not work). platform='custom' because
-- BookTix has no dedicated ScrapingPlatform enum value. Verified: 12 shows
-- scraped in prod (4 productions, incl. PNR Improv comedy).
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, visible, status)
SELECT 'Makeshift Theater Akron', '732 West Exchange Street, Akron, OH 44302', 'https://www.makeshiftakron.org', 'Akron', 'OH', '44302', 'America/New_York', 'US', 'club', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Makeshift Theater Akron');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'custom'::"ScrapingPlatform", 'booktix', 'https://makeshift.booktix.com/dept/main', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Makeshift Theater Akron'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'booktix');
