-- Onboard The Laughing Tap via Etix (venue mode) — TASK-2985
--
-- The Laughing Tap (761 N Jefferson St, Milwaukee, WI) is an all-comedy club
-- (operated by Milwaukee Comedy LLC). Its own site (laughingtap.com) lists shows
-- as individual Etix event links; the Etix venue_id is 27614 (confirmed via the
-- event page "The Laughing Tap Comedy Club"). Wired to the generic etix scraper
-- (source_url = https://www.etix.com/ticket/v/27614).
--
-- NOTE: Etix is DataDome-protected. Local verification returned 0 (WAF block on
-- residential IP); production GHA scrapes Etix successfully for existing venues
-- (Zanies, Funny Bone, Laugh Patriot Place) via the capsolver/Decodo path, so
-- this venue will populate on the nightly run. venue_id + live comedy calendar
-- confirmed independently (laughingtap.com lists 18 upcoming touring comedians).
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Laughing Tap', '761 N Jefferson St, Milwaukee, WI 53202', 'http://laughingtap.com/', 'Milwaukee', 'WI', '53202', 'America/Chicago', 'US', 'club', 'ChIJQ1eisdsZBYgRzVL3QV9f0Qs', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Laughing Tap');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'etix'::"ScrapingPlatform", 'etix', 'https://www.etix.com/ticket/v/27614', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'The Laughing Tap'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'etix');
