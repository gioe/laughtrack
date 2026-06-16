-- Onboard Amish Country Theater (Berlin, OH) — TASK-2897
--
-- Amish Country Theater (4365 OH-39, Berlin, OH 44610; amishcountrytheater.com)
-- is a family/variety comedy theater in Ohio Amish Country. Its own /tickets page
-- embeds a VBO Tickets plugin (connect.vbotickets.com, siteid
-- 4A6B1B18-AF73-4099-9005-D183148A1A68) that renders a multi-event "showevents"
-- listing. Handled by the new generic `vbo_tickets` scraper, which acquires a VBO
-- session from the loadplugin URL (source_url) then parses the current-events
-- listing (name, date, price). Fixed venue → visible=true.
-- Verified: 176 shows scraped in prod.
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Amish Country Theater', '4365 OH-39, Berlin, OH 44610', 'https://amishcountrytheater.com', 'Berlin', 'OH', '44610', 'America/New_York', 'US', 'club', 'ChIJ1ahVAf4QN4gR4zAxZOTkUKQ', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Amish Country Theater');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'custom'::"ScrapingPlatform", 'vbo_tickets', 'https://plugin.vbotickets.com/plugin/loadplugin?siteid=4A6B1B18-AF73-4099-9005-D183148A1A68&page=ListEvents', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Amish Country Theater'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'vbo_tickets');
