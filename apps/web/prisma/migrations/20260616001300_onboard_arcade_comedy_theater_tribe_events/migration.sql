-- TASK-2875: Onboard Arcade Comedy Theater (Pittsburgh, PA), discovered via the
-- discover-comedy-venues skill (objective #2, ZIP 44622). Downtown Pittsburgh's
-- dedicated stand-up/improv comedy theater. Its site runs the WordPress
-- "The Events Calendar" (Tribe) plugin, which exposes a public REST API at
-- /wp-json/tribe/events/v1/events — scraped by the generic `the_events_calendar`
-- scraper. Fixed venue → visible=true. Verified 26 shows scraped in prod.
-- Idempotent (NOT EXISTS guards) so it no-ops where rows already exist (prod)
-- and reproduces state on fresh databases.


-- Arcade Comedy Theater (Tribe Events / The Events Calendar)
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Arcade Comedy Theater', '943 Liberty Ave, Pittsburgh, PA 15222, USA', 'https://www.arcadecomedytheater.com', 'Pittsburgh', 'PA', '15222', 'America/New_York', 'US', 'club', 'ChIJ_____1bxNIgRTeuet-WXiZ4', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Arcade Comedy Theater');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'tribe_events'::"ScrapingPlatform", 'the_events_calendar', 'https://www.arcadecomedytheater.com/wp-json/tribe/events/v1/events', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Arcade Comedy Theater'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'the_events_calendar');
