-- Onboard The Crib Comedy Playspace via Eventbrite organizer — TASK-2963
--
-- The Crib Comedy Playspace (2715 W Madison St, Chicago, IL) is an all-comedy
-- venue (Instagram + Square site, no scrapable own calendar). Its shows are
-- ticketed via the Eventbrite organizer "The Crib Comedy Playspace"
-- (organizer_id 120368001981). Organizer mode is used; the per-venue upsert
-- fuzzy-reconciles the Eventbrite venue (also named "The Crib Comedy Playspace",
-- Chicago/IL) to this visible club, so shows land here rather than a duplicate.
--
-- Verified: real scrape returned 2 shows attached to this club.
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Crib Comedy Playspace', '2715 W Madison St, Chicago, IL 60612', 'https://thecribcomedy.square.site/', 'Chicago', 'IL', '60612', 'America/Chicago', 'US', 'club', 'ChIJ4-7fjnctDogRPmUCpGZ1nfY', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Crib Comedy Playspace');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/120368001981', '120368001981', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'The Crib Comedy Playspace'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');
