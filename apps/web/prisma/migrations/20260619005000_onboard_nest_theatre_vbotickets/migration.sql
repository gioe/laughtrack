-- Onboard The Nest Theatre (Columbus, OH) — TASK-2877
--
-- The Nest Theatre (2643 N High St) is a Columbus improv + stand-up comedy
-- theatre. Its own site (nesttheatre.com/shows/) hydrates its listings from a
-- VBO Tickets plugin (plugin.vbotickets.com, siteid 5D584EB6-...). A net-new
-- venue scraper (scraper_key=nest_theatre) reads the VBO "showevents" grid,
-- keeps only data-event-category="Live Shows" (classes/camps/workshops are
-- excluded), and expands recurring listings into one show per upcoming date.
-- Verified: 19 shows scraped. Fixed venue → visible=true.
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Nest Theatre', '2643 N High St, Columbus, OH 43202, USA', 'https://nesttheatre.com/', 'Columbus', 'OH', 'America/New_York', 'US', 'club', 'ChIJe4VjWzaPOIgRjuXnR1D1PQA', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Nest Theatre');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'custom'::"ScrapingPlatform", 'nest_theatre', 'https://nesttheatre.com/shows/', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'The Nest Theatre'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'nest_theatre');
