-- TASK-2878: Onboard The Hashtag Comedy Club (Columbus, OH), discovered via the
-- discover-comedy-venues skill (objective #2, ZIP 44622). A stand-up/improv/sketch
-- comedy club. Its site runs on Squarespace; the "Upcoming Comedy Shows" events
-- collection (id 5adfb0b98a922d758d0d6d2a) is exposed via the Squarespace
-- GetItemsByMonth API — scraped by the generic `squarespace` scraper. Fixed venue
-- → visible=true. Verified 22 shows scraped in prod.
-- Idempotent (NOT EXISTS guards) so it no-ops where rows already exist (prod)
-- and reproduces state on fresh databases.


-- The Hashtag Comedy Club (Squarespace events collection)
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Hashtag Comedy Club', '1253 N High St, Columbus, OH 43201, USA', 'https://www.hashtagcomedy.com', 'Columbus', 'OH', '43201', 'America/New_York', 'US', 'club', 'ChIJQ0ZcG0mPOIgRdJfQGytkljA', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Hashtag Comedy Club');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'squarespace'::"ScrapingPlatform", 'squarespace', 'https://www.hashtagcomedy.com/api/open/GetItemsByMonth?collectionId=5adfb0b98a922d758d0d6d2a', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'The Hashtag Comedy Club'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'squarespace');
