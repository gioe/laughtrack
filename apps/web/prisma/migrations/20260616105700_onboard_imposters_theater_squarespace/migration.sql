-- TASK-2888: Onboard Imposters Theater (Cleveland, OH), discovered via the
-- discover-comedy-venues skill (objective #2, ZIP 44622). Cleveland's home for
-- improv/sketch/stand-up comedy (incl. "Imposters BIG Improv Comedy Night").
-- Its site runs on Squarespace; the "Schedule" events collection
-- (id 5eba1742a2f250476647352e) is exposed via the Squarespace GetItemsByMonth
-- API — scraped by the generic `squarespace` scraper. Fixed venue → visible=true.
-- Verified 137 shows scraped in prod.
-- Idempotent (NOT EXISTS guards) so it no-ops where rows already exist (prod)
-- and reproduces state on fresh databases.


-- Imposters Theater (Squarespace events collection)
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Imposters Theater', '4828 Lorain Ave, Cleveland, OH 44102, USA', 'https://www.imposterstheater.com', 'Cleveland', 'OH', '44102', 'America/New_York', 'US', 'club', 'ChIJNQJPhIH7MIgRvFHR2xg5UA8', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Imposters Theater');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'squarespace'::"ScrapingPlatform", 'squarespace', 'https://www.imposterstheater.com/api/open/GetItemsByMonth?collectionId=5eba1742a2f250476647352e', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Imposters Theater'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'squarespace');
