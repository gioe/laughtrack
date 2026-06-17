-- Onboard Jilly's Music Room (Akron, OH) — TASK-2926
--
-- Jilly's Music Room (111 N Main St, Akron OH 44308; jillysmusicroom.com) is a
-- live-music room that also hosts comedy (e.g. "Mid-Life Crisis: A Comedy Improv
-- Troupe", "Silly at Jilly's" w/ Krackpots). Fixed venue → visible=TRUE.
--
-- Datasource: EventON WordPress calendar plugin (custom post type ajde_events,
-- v4.0.6). The REST API lists events but exposes no start dates; the scrapable
-- seam is the frontend calendar loader at /wp-admin/admin-ajax.php
-- (action=eventon_init_load), which returns upcoming events with unix start
-- times. Handled by the NEW generic `eventon` scraper. platform='custom'
-- because EventON has no dedicated ScrapingPlatform enum value.
--
-- Jilly's is primarily a music venue, so metadata.event_type_filter='comedy'
-- restricts the scrape to events tagged with EventON's `comedy` event_type term
-- (keeps the comedy-only DB clean). Verified: 1 upcoming comedy show scraped
-- live (58 future events total, 1 comedy-tagged).
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, visible, status)
SELECT 'Jilly''s Music Room', '111 North Main Street, Akron, OH 44308', 'https://jillysmusicroom.com', 'Akron', 'OH', '44308', 'America/New_York', 'US', 'club', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Jilly''s Music Room');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'custom'::"ScrapingPlatform", 'eventon', 'https://jillysmusicroom.com', 0, TRUE, '{"event_type_filter": "comedy"}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Jilly''s Music Room'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventon');
