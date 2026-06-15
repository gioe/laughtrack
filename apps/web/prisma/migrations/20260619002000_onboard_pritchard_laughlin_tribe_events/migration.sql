-- TASK-2865: Onboard Pritchard Laughlin Civic Center (Cambridge, OH), discovered
-- via the discover-comedy-venues skill (objective #2, ZIP 44622). A multipurpose
-- civic center that programs national stand-up tours alongside concerts and
-- theater. Its site runs the WordPress "The Events Calendar" (Tribe) plugin,
-- which exposes a public REST API at /wp-json/tribe/events/v1/events — scraped
-- by the generic `the_events_calendar` scraper. Fixed venue → visible=true.
-- Idempotent (NOT EXISTS guards) so it no-ops where rows already exist (prod)
-- and reproduces state on fresh databases.


-- Pritchard Laughlin Civic Center (Tribe Events / The Events Calendar)
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Pritchard Laughlin Civic Center', '7033 Glenn Hwy, Cambridge, OH 43725, USA', 'https://pritchardlaughlin.com', 'Cambridge', 'OH', '43725', 'America/New_York', 'US', 'club', 'ChIJ6eEQeg62N4gRclC0K0c5YXM', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Pritchard Laughlin Civic Center');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'tribe_events'::"ScrapingPlatform", 'the_events_calendar', 'https://pritchardlaughlin.com/wp-json/tribe/events/v1/events', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Pritchard Laughlin Civic Center'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'the_events_calendar');
