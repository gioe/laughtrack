-- Onboard Sick Puppies Comedy / Doghouse Theater (Delray Beach, FL) — TASK-3354,
-- objective #11 discover-comedy-venues near Miami 33130 / Fort Lauderdale 33301.
--
-- Sick Puppies Comedy is the resident improv company operating the Doghouse Theater
-- (one room at 105 NW 5th Ave). Its own site (sickpuppiescomedy.com) is a Wix site
-- running the native Wix Events app — recurring improv + stand-up series (Doghouse
-- Theater Improv Comedy Show, First Friday Stand-Up, "Longer, Harder, Improv",
-- Student Showcase). The /shows page hydrates its listings from the Wix Events
-- widget; JSON-LD carries no Event objects.
--
-- Datasource: native Wix Events, wired to the generic `wix_events` scraper:
-- source_url = the Wix site root, wix_event_id = the Events-widget compId
-- (comp-llkywmpd, found on the /shows page under the Wix Events appDef
-- 140603ad-af8d-84a5-2c80-a0f60cb47351). The scraper resolves the Wix instance
-- token from the site root itself, then calls /_api/wix-one-events-server/web/
-- paginated-events/viewer. All-comedy venue -> no comedy_filter needed.
--
-- Fixed venue (its own theater room) -> visible=true.
--
-- Verified: `make scrape-club-id ID=<club_id>` scraped 41 shows (4 recurring comedy
-- series, 2026-06-28 through 2026-12-27) onto the single club.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible). Guard on name OR google_place_id (the
--    operator and the Doghouse venue place_ids both resolve to this one room).
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Sick Puppies Comedy',
       '105 NW 5th Ave',
       'https://www.sickpuppiescomedy.com',
       'Delray Beach', 'FL', '33444',
       'America/New_York', 'US', 'club',
       'ChIJo4nkbRDi2IgR__HQoj7tCJA',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'Sick Puppies Comedy'
     OR google_place_id IN ('ChIJo4nkbRDi2IgR__HQoj7tCJA', 'ChIJdXsfXb7f2IgRKpc82ZRZisc')
);

-- 2. The wix_events scraping source (venue root + events-widget compId). platform
-- 'wix_events' is a curated enum value; the scraper reads the compId from
-- wix_event_id. Locate the club by name OR google_place_id for idempotency parity.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, wix_event_id, priority, enabled, metadata)
SELECT c.id, 'wix_events', 'wix_events',
       'https://www.sickpuppiescomedy.com',
       'comp-llkywmpd',
       0, true, '{}'::jsonb
FROM clubs c
WHERE (c.name = 'Sick Puppies Comedy' OR c.google_place_id = 'ChIJo4nkbRDi2IgR__HQoj7tCJA')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'wix_events'
  );
