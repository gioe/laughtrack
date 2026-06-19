-- Onboard Mystic Vines Theater & Events via TicketLeap (comedy-filtered) — TASK-2970
--
-- Mystic Vines (219 W St Charles Rd, Villa Park, IL) is a mixed-use venue:
-- its TicketLeap org "mysticvines" (events.ticketleap.com/events/mysticvines)
-- runs comedy alongside dance classes (Bachata/Salsa/Ballroom). The ticketleap
-- scraper now supports opt-in comedy filtering (TASK-3011), so the source sets
-- metadata.comedy_filter=true to keep comedy only.
--
-- Verified: real scrape with the filter returned 1 comedy show ("Cutthroat
-- Improv"); the 3 dance-class events were dropped.
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Mystic Vines Theater & Events', '219 W St Charles Rd, Villa Park, IL 60181', 'https://www.mysticvines.com/', 'Villa Park', 'IL', '60181', 'America/Chicago', 'US', 'club', 'ChIJg1H8_zBNDogRWZyKpFFZVMc', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Mystic Vines Theater & Events');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'ticketleap'::"ScrapingPlatform", 'ticketleap', 'https://events.ticketleap.com/events/mysticvines', 0, TRUE, '{"comedy_filter": true}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Mystic Vines Theater & Events'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'ticketleap');
