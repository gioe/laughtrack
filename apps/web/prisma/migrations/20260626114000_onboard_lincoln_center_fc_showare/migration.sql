-- Onboard The Lincoln Center (Fort Collins, CO) — TASK-3432, objective #13
-- (discover-comedy-venues near 80202).
--
-- The Lincoln Center is Fort Collins' municipal performing-arts center
-- (lctix.com). Its box office runs on accesso ShoWare under the white-label host
-- tickets.lctix.com (footer: "ticketing System provided by accesso ShoWare").
-- The generic `showare` scraper derives the JSON performance-list endpoint from
-- the host:
--   https://tickets.lctix.com/include/widgets/events/performancelist.asp
--       ?action=perf&listPageSize=100&listMaxSize=100&page=1
-- which returns ShoWare `performance` rows (Event title, PerformanceDateTime
-- "Saturday, February 20, 2027 7:30:00 PM", PerformanceMinPrice, EventID/
-- PerformanceID). No new code is needed — this maps to the existing
-- apps/scraper/.../scrapers/implementations/api/showare scraper.
--
-- It is a multi-purpose hall (Fort Collins Symphony, ballet, National Geographic
-- Live, Broadway tours, movies-in-concert) that also books genuine stand-up.
-- The venue reliably co-brands real comedy with "Comedy Works" (a Denver comedy
-- promoter). At onboarding the live ShoWare feed (77 performances) carried 4
-- comedy shows:
--   * GARY GULMAN'S 7TH HOUR (Presented by LC LIVE and Comedy Works)
--   * MARC MARON: YAMMERING INTO THE VOID TOUR (and Comedy Works)
--   * WHOSE LIVE ANYWAY? WITH SPECIAL GUEST DAVE FOLEY (and Comedy Works) — improv
--   * #IMOMSOHARD: The Flashback Tour
-- so the source carries an opt-in `include_title_patterns` comedy allowlist (the
-- filter is OFF by default, but a multi-purpose ShoWare host MUST scope to comedy
-- or it would ingest the symphony/Broadway calendar). A 0-comedy window is
-- expected when no stand-up is currently listed; comedy auto-populates when the
-- next show is announced.
--
-- The host is NOT *.showare.com, so the scraper requires
-- `metadata.showare_whitelabel=true` to allow the white-label host.
--
-- Fixed venue (it is its own room) => visible=true.
--
-- Idempotent: NOT EXISTS guards so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database. (If discover-comedy-venues
-- pre-inserted a club row under a different exact name, the scraping_sources
-- insert below would not attach to it — verify post-apply that the showare row
-- landed on the intended club via `make scrape-club-id`.)

-- 1. Venue club (fixed venue, visible).
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Lincoln Center',
       '417 W Magnolia St, Fort Collins, CO 80521, USA',
       'http://www.lctix.com/',
       'Fort Collins', 'CO', '80521', 'America/Denver', 'US', 'club',
       'ChIJN6-m6F5KaYcRvg4wGJ33ziQ', true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Lincoln Center');

-- 2. ShoWare scraping source (no unique constraint beyond PK, so guard with
--    NOT EXISTS on (club_id, scraper_key)). source_url = ShoWare default.asp;
--    showare_whitelabel allows the tickets.lctix.com host;
--    include_title_patterns keeps only the comedy bookings.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom', 'showare',
       'https://tickets.lctix.com/default.asp', 0, true,
       '{"showare_whitelabel": true, "include_title_patterns": ["Comedy Works", "#IMOMSOHARD", "comedy", "comedian", "stand[ -]?up"]}'::jsonb
FROM clubs c
WHERE c.name = 'The Lincoln Center'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'showare'
  );
