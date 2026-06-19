-- Onboard Des Plaines Theatre (etix, comedy-filtered) + fix Laughing Tap URL
-- TASK-2969 / TASK-3010
--
-- 1) Des Plaines Theatre (1476 Miner St, Des Plaines, IL) is a mixed-use theater
--    (rock/country/magic/comedy) on Etix (venue_id 20795). The etix scraper now
--    supports opt-in comedy filtering (TASK-3010), so the source sets
--    metadata.comedy_filter=true to keep comedy only (name-only touring comics
--    are caught by the known-comedian heuristic).
--    Onboarded HIDDEN (visible=false): Etix is DataDome-protected so the scrape
--    can't be verified on a residential IP — it populates on the GHA nightly
--    (like Zanies/Funny Bone). Flip to visible after confirming comedy-only
--    output (tracked on TASK-2969).
--
-- 2) Fix The Laughing Tap source_url (TASK-2985): the etix scraper extracts the
--    venue_id via the `/v/(\d+)/` pattern, which needs a trailing slug segment.
--    The original onboarding row had no trailing segment, so add one. Idempotent:
--    the UPDATE only touches the un-fixed value.
--
-- Idempotent: NOT EXISTS-guarded INSERTs + a targeted UPDATE; no-ops on re-run.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Des Plaines Theatre', '1476 Miner St, Des Plaines, IL 60016', 'https://desplainestheatre.com/', 'Des Plaines', 'IL', '60016', 'America/Chicago', 'US', 'club', 'ChIJlQSK_Zi3D4gRj9P_3VnusZQ', FALSE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Des Plaines Theatre');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'etix'::"ScrapingPlatform", 'etix', 'https://www.etix.com/ticket/v/20795/des-plaines-theatre', 0, TRUE, '{"comedy_filter": true}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Des Plaines Theatre'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'etix');

UPDATE scraping_sources
SET source_url = 'https://www.etix.com/ticket/v/27614/the-laughing-tap'
WHERE scraper_key = 'etix'
  AND source_url = 'https://www.etix.com/ticket/v/27614';
