-- Onboard Comedians You Should Know (CYSK) via Eventbrite organizer — TASK-2958
--
-- CYSK is a Chicago stand-up showcase brand. Its own site
-- (comediansyoushouldknow.com/upcoming-shows) carries no structured event data
-- (JSON-LD is WebSite-only); it links out to its Eventbrite organizer
-- "cysk" (organizer_id 29670593401) which holds the real show listings.
-- The organizer runs shows at varying venues (e.g. its weekly Wednesday show at
-- Timothy O'Toole's Pub Chicago), so Eventbrite ORGANIZER mode is required —
-- venue mode returns 0 for foreign venues.
--
-- Per the roving-producer pattern (cf. Lucky Haskin Productions TASK-2917,
-- The Comedy Bar - Pittsburgh TASK-2874): this anchor club is a HIDDEN synthetic
-- proxy (visible=FALSE) that holds the scraping_sources row; the eventbrite
-- scraper surfaces the organizer's shows under auto-created per-venue clubs.
-- scraper_key=eventbrite (existing generic scraper), organizer mode
-- (source_url contains /o/, eventbrite_id = organizer id).
--
-- Verified: real scrape returned 1 comedy show, routed to an auto-created
-- visible per-venue club "Timothy O'Toole's Pub Chicago" (the recurring
-- CYSK Wednesday showcase on 2026-06-25).
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Comedians You Should Know (CYSK)', '622 N Fairbanks Ct, Chicago, IL 60611', 'http://www.comediansyoushouldknow.com/', 'Chicago', 'IL', '60611', 'America/Chicago', 'US', 'club', 'ChIJHeQm7qosDogRtuACcQ4dqP4', FALSE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Comedians You Should Know (CYSK)');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/29670593401', '29670593401', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Comedians You Should Know (CYSK)'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');
