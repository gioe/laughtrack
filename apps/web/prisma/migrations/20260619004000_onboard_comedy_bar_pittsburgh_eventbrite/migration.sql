-- Onboard The Comedy Bar - Pittsburgh (Pittsburgh, PA) — TASK-2874
--
-- The venue (2151 Babcock Blvd) hydrates its show listings from its Eventbrite
-- organizer (106278430571), embedded as widgets on its WordPress site
-- (comedybar.com/pittsburgh). The Eventbrite organizer is modeled as a
-- production company, so this anchor club is a HIDDEN synthetic proxy
-- (visible=FALSE) that holds the scraping_sources row; the scraper surfaces the
-- organizer's shows under an auto-created per-venue club ("The Comedy Bar @
-- Remo's", same 2151 Babcock Blvd address, visible). Verified: 42 shows scraped.
--
-- scraper_key=eventbrite (existing generic scraper, reads eventbrite_id).
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Comedy Bar - Pittsburgh', '2151 Babcock Blvd, Pittsburgh, PA 15209, USA', 'https://www.comedybar.com/pittsburgh', 'Pittsburgh', 'PA', 'America/New_York', 'US', 'club', 'ChIJd9vlmirzNIgRAhmOmqb5XG0', FALSE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Comedy Bar - Pittsburgh');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/106278430571', '106278430571', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'The Comedy Bar - Pittsburgh'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');
