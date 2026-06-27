-- Onboard Shamrock Comedy Club at The Field Irish Pub (Fort Lauderdale, FL) —
-- TASK-3362, objective #11 discover-comedy-venues near Miami 33130 / Fort
-- Lauderdale 33301.
--
-- Shamrock Comedy Club is an all-comedy club booking national headliners (Nick
-- Griffin, Matthew Broussard, Chris Renois, Josh Francis, ...) at a fixed room,
-- The Field Irish Pub on Griffin Rd. Discovery hinted "Squarespace + Eventbrite",
-- but the live site (shamrockcomedyclub.com) is actually a WIX site running the
-- native Wix Events app; its /shows page hydrates from the Wix Events widget
-- (events-widget compId comp-ju0zof0q, appDef 140603ad-af8d-84a5-2c80-a0f60cb47351).
-- Eventbrite is only the per-show ticketing link-out, so per the prefer-club-website
-- principle we scrape the venue's own Wix Events feed (show_page_url lands on the
-- venue's /event-details/ pages), not Eventbrite.
--
-- Datasource: native Wix Events, wired to the generic `wix_events` scraper:
-- source_url = the Wix site root, wix_event_id = the Events-widget compId
-- (comp-ju0zof0q). The scraper resolves the Wix instance token from the site root,
-- then calls /_api/wix-one-events-server/web/paginated-events/viewer. All-comedy
-- venue -> no comedy_filter needed.
--
-- Fixed venue (the club always plays the one Field Irish Pub room) -> visible=true.
--
-- Verified: `make scrape-club-id ID=<club_id>` scraped 6 shows (national headliners,
-- 2026-07-21 through 2026-12-15) onto the single club, each show_page_url on the
-- venue's own site (club 11460, source 7028).
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible). Guard on name OR google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Shamrock Comedy Club',
       '3281 Griffin Rd, Fort Lauderdale, FL 33312',
       'https://www.shamrockcomedyclub.com',
       'Fort Lauderdale', 'FL', '33312',
       'America/New_York', 'US', 'club',
       'ChIJixp_sfGr2YgRzFEjQxktC0M',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'Shamrock Comedy Club'
     OR google_place_id = 'ChIJixp_sfGr2YgRzFEjQxktC0M'
);

-- 2. The wix_events scraping source (venue root + events-widget compId). platform
-- 'wix_events' is a curated enum value; the scraper reads the compId from
-- wix_event_id. Locate the club by name OR google_place_id for idempotency parity.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, wix_event_id, priority, enabled, metadata)
SELECT c.id, 'wix_events', 'wix_events',
       'https://www.shamrockcomedyclub.com',
       'comp-ju0zof0q',
       0, true, '{}'::jsonb
FROM clubs c
WHERE (c.name = 'Shamrock Comedy Club' OR c.google_place_id = 'ChIJixp_sfGr2YgRzFEjQxktC0M')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'wix_events'
  );
