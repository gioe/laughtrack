-- TASK-2889: Make The Winchester Music Tavern (Lakewood, OH) onboarding reproducible.
-- Discovered via discover-comedy-venues (objective #2, ZIP 44622). The venue hosts
-- recurring comedy (Henceforth Comedy / "Secret Society Comedy" Tuesdays + touring
-- acts) and runs its OWN Eventbrite organizer (id 277070643), distinct from
-- Henceforth's organizer (25799034879, covered by the eventbrite_comedy_cluster_44622
-- migration). Club 8695 + its organizer source were created at scrape time during
-- TASK-2869's Eventbrite venue-split, so no migration reproduced them and the
-- venue-split stub had blank website/timezone/country/google_place_id. This migration
-- makes the club + its own organizer source reproducible on fresh DBs and backfills
-- the missing metadata. Verified 29 shows scraped in prod via organizer 277070643.
-- Idempotent (NOT EXISTS / COALESCE guards) so it no-ops where rows already exist.


-- The Winchester Music Tavern (own Eventbrite organizer 277070643)
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Winchester Music Tavern', '12112 Madison Ave, Lakewood, OH 44107, USA', 'https://www.thewinchestermusictavern.com', 'Lakewood', 'OH', '44107', 'America/New_York', 'US', 'club', 'ChIJb8Q8TvfxMIgRU3CW9Ef9www', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Winchester Music Tavern');

-- Backfill metadata on the venue-split-created stub (idempotent: only fills blanks)
UPDATE clubs SET
  website = COALESCE(NULLIF(website, ''), 'https://www.thewinchestermusictavern.com'),
  timezone = COALESCE(timezone, 'America/New_York'),
  country = COALESCE(country, 'US'),
  google_place_id = COALESCE(google_place_id, 'ChIJb8Q8TvfxMIgRU3CW9Ef9www')
WHERE name = 'The Winchester Music Tavern';

-- Wire Winchester's own Eventbrite organizer (277070643)
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com', '277070643', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'The Winchester Music Tavern'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');
