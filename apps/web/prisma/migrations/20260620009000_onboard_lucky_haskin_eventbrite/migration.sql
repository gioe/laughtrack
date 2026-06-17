-- Onboard Garage Bar Willoughby comedy via Lucky Haskin Productions — TASK-2917
--
-- Garage Bar Willoughby (37825 Vine St) runs a recurring stand-up series
-- (Bill Squire headlining) but has no own website (Facebook-only) and no
-- venue-specific ticketing. Its comedy is ticketed exclusively through the
-- Eventbrite organizer "Lucky Haskin Productions" (organizer_id 1397408865), a
-- COMEDY-FOCUSED roving producer that also runs comedy at The Brothers Lounge,
-- Old 86, etc. Eventbrite venue-mode returns 0 for foreign venues, so the only
-- way to capture Garage Bar's comedy is ORGANIZER mode on the producer.
--
-- Per the roving-producer pattern (cf. The Comedy Bar - Pittsburgh, TASK-2874):
-- this anchor club is a HIDDEN synthetic proxy (visible=FALSE) that holds the
-- scraping_sources row; the eventbrite scraper surfaces the organizer's shows
-- under auto-created/resolved per-venue clubs (e.g. Garage Bar Willoughby, and
-- The Brothers Lounge which already exists as club 8703). scraper_key=eventbrite
-- (existing generic scraper), organizer mode (source_url contains /o/,
-- eventbrite_id = organizer id).
--
-- Verified: real scrape returned 1 comedy show, routed to the existing
-- The Brothers Lounge club. Garage Bar dates surface here when next posted
-- (the Jan 2026 date had already passed at onboarding time).
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, visible, status)
SELECT 'Lucky Haskin Productions', '37825 Vine St, Willoughby, OH 44094', 'https://www.eventbrite.com/o/1397408865', 'Willoughby', 'OH', '44094', 'America/New_York', 'US', 'club', FALSE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Lucky Haskin Productions');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/1397408865', '1397408865', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Lucky Haskin Productions'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');
