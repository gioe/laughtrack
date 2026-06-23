-- Onboard Sacramento Comedy Spot (Sacramento, CA) — TASK-3201
--
-- Sacramento Comedy Spot (1050 20th St #130, Sacramento, CA 95811;
-- saccomedyspot.com) is a comedy-dedicated venue running stand-up showcases,
-- open mics, and improv 6 nights/week. Its own /calendar page hydrates its
-- listings from a VBO Tickets plugin (connect.vbotickets.com / plugin.vbotickets.com,
-- SiteID C1822884-45A0-4B3D-83FE-A53AA0FBE93C, Page=ListEvents). Handled by the
-- generic `vbo_tickets` scraper, which acquires a VBO session from the loadplugin
-- URL (source_url) then parses the current-events listing.
--
-- The listing carries three data-event-category values: "Comedy Spot Shows"
-- (the actual stand-up/improv shows — KEEP), "Comedy Spot Classes" (improv/
-- stand-up classes — DROP), and "Holiday/Other" (holiday-closure placeholders
-- like Thanksgiving/Christmas — DROP). A category_filter in metadata keeps only
-- "Comedy Spot Shows". Fixed venue → visible=true.
-- Verified: 33 shows scraped.
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Sacramento Comedy Spot', '1050 20th St #130, Sacramento, CA 95811', 'https://saccomedyspot.com', 'Sacramento', 'CA', '95811', 'America/Los_Angeles', 'US', 'club', 'ChIJPwTgM9vQmoARdRgAzvTSLbQ', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Sacramento Comedy Spot');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'custom'::"ScrapingPlatform", 'vbo_tickets', 'https://plugin.vbotickets.com/plugin/loadplugin?siteid=C1822884-45A0-4B3D-83FE-A53AA0FBE93C&page=ListEvents', 0, TRUE, '{"category_filter": "Comedy Spot Shows"}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Sacramento Comedy Spot'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'vbo_tickets');
