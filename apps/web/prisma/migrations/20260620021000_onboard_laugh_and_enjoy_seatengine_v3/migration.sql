-- Onboard Laugh And Enjoy Comedy Club via SeatEngine v3 — TASK-2972 / TASK-3009
--
-- Laugh And Enjoy (2005 Franciscan Way, West Chicago, IL) is an all-comedy club
-- on SeatEngine v3 (venue UUID c91f790c-4cb1-41cd-84fc-bee3b91a0b61). Onboarding
-- was blocked by the v3 GraphQL soldOut schema drift (TASK-3009), now fixed.
--
-- Onboarded HIDDEN (visible=false): the venue currently has ZERO upcoming events
-- in its v3 feed (confirmed: eventsList returns [] even over a wide date range;
-- the scraper runs cleanly with no error). The source is enabled so the nightly
-- run picks up shows when the venue schedules them; flip visible once
-- total_shows > 0.
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Laugh And Enjoy Comedy Club', '2005 Franciscan Way, West Chicago, IL 60185', 'https://laughandenjoy.com/', 'West Chicago', 'IL', '60185', 'America/Chicago', 'US', 'club', 'ChIJ9eo285gBD4gRBrZeR0lio14', FALSE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Laugh And Enjoy Comedy Club');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, seatengine_v3_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'seatengine_v3'::"ScrapingPlatform", 'seatengine_v3', 'https://laughandenjoy.com/', 'c91f790c-4cb1-41cd-84fc-bee3b91a0b61', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Laugh And Enjoy Comedy Club'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'seatengine_v3');
