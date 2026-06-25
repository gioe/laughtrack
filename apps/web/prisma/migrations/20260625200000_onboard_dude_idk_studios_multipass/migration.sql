-- Onboard Dude, IDK Studios (Denver, CO) — TASK-3396, objective #13
-- (discover-comedy-venues near 80202).
--
-- Dude, IDK Studios is a fixed comedy/podcast studio at 2801 N Downing St that
-- runs a busy stand-up calendar (Macey Isaacs, Shane Torres, JT Tomlinson,
-- Lisandra Vazquez, Good Night Denver, ...). Its own Wix site
-- (dudeidkstudios.com /event-list) lists the shows, but the native Wix Events
-- app is empty ("No events at the moment") — the real listings render from a Wix
-- dynamic-data collection whose buy links all point at the venue's box office on
-- the Multipass ticketing platform: https://denvercomedy.multipass.com/
--
-- Multipass (multipass.com) is a server-rendered ticketing platform. The venue
-- subdomain root lists every show as a `div.eventCard2026` card with title,
-- date/time, price and ticket URL in static HTML — no detail-page fetch needed.
-- No existing scraper matched, so this ships a new GENERIC `multipass` scraper
-- (apps/scraper/.../scrapers/implementations/api/multipass/); a future Multipass
-- venue needs only a scraping_sources row with source_url = its subdomain root.
--
-- The static HTML carries ALL events (past + future); the live page hides past
-- ones via a "Show Past Events" toggle. The framework does NOT drop past-dated
-- shows, so the scraper filters to upcoming-only. The card date string omits the
-- year, which is inferred from the printed weekday + month/day.
--
-- Fixed venue (its own room) => visible=true.
-- Verified: make scrape-club-id => 9 shows (2026-07-03 .. 2026-08-28).
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Venue club (fixed venue, visible).
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Dude, IDK Studios',
       '2801 N Downing St, Denver, CO 80205, USA',
       'https://www.dudeidkstudios.com',
       'Denver', 'CO', '80205', 'America/Denver', 'US', 'club',
       'ChIJ-9_16NR5bIcRnmHm2b9VJF0', true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Dude, IDK Studios');

-- 2. Multipass scraping source (no unique constraint beyond PK, so guard with
--    NOT EXISTS on (club_id, scraper_key)). source_url = venue box-office root.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom', 'multipass',
       'https://denvercomedy.multipass.com/', 0, true, '{}'
FROM clubs c
WHERE c.name = 'Dude, IDK Studios'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'multipass'
  );
