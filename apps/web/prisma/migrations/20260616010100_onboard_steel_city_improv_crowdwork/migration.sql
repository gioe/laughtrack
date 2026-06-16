-- TASK-2881: Onboard Steel City Improv Theater (Pittsburgh, PA), discovered via the
-- discover-comedy-venues skill (objective #2, ZIP 44622). An improv theater (classes
-- + shows). Its WordPress site embeds Crowdwork; the venue's shows are exposed via
-- the Crowdwork v2 API at /api/v2/steelcityimprovtheater/shows — scraped by the
-- generic `crowdwork` scraper. Fixed venue → visible=true. Verified 3 shows scraped
-- in prod.
-- Idempotent (NOT EXISTS guards) so it no-ops where rows already exist (prod)
-- and reproduces state on fresh databases.


-- Steel City Improv Theater (Crowdwork)
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Steel City Improv Theater', '5950 Ellsworth Ave, Pittsburgh, PA 15232, USA', 'https://steelcityimprov.com', 'Pittsburgh', 'PA', '15232', 'America/New_York', 'US', 'club', 'ChIJWVygRXPyNIgR-H6gkA8KMTM', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Steel City Improv Theater');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'crowdwork'::"ScrapingPlatform", 'crowdwork', 'https://crowdwork.com/api/v2/steelcityimprovtheater/shows', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Steel City Improv Theater'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'crowdwork');
