-- Onboard The Punchline Comedy Club (Atlanta / Sandy Springs, GA) — TASK-3364,
-- objective #12 discover-comedy-venues near Atlanta 30303.
--
-- THE major Atlanta stand-up club (Outback Presents / Live Nation operated). Its
-- own WordPress site (punchline.com, Cloudflare-fronted) runs The Events Calendar
-- (Modern Tribe) plugin and exposes its full upcoming-shows feed at the Tribe REST
-- API endpoint /wp-json/tribe/events/v1/events (116 events). All-comedy club, so no
-- comedy filter is needed.
--
-- Datasource: The Events Calendar (Tribe) REST API, wired to the existing
-- `the_events_calendar` scraper: platform='tribe_events', source_url = the Tribe
-- events endpoint. (Plain curl gets a Cloudflare 406; the scraper's
-- browser-impersonating fetch passes — the verified live scrape confirms it.)
--
-- Fixed venue (its own club) -> visible=true.
--
-- Verified: `make scrape-club-id ID=<club_id>` scraped 116 events -> 94 upcoming
-- shows persisted across 38 distinct stand-up acts (e.g. Michael Palascak, Tara
-- Cannistraci, Fumi Abe, Gus Constantellis), 2026-06-27 through 2026-12-12.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible). Guard on name OR google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Punchline Comedy Club',
       '3652 Roswell Rd',
       'https://www.punchline.com',
       'Atlanta', 'GA', '30342',
       'America/New_York', 'US', 'club',
       'ChIJhzE5oJcO9YgRE5wQsfexfqw',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'The Punchline Comedy Club'
     OR google_place_id = 'ChIJhzE5oJcO9YgRE5wQsfexfqw'
);

-- 2. The the_events_calendar scraping source. platform 'tribe_events' is a curated
-- enum value; the scraper reads the Tribe events endpoint from source_url. Locate
-- the club by name OR google_place_id for idempotency parity with the guard above.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'tribe_events', 'the_events_calendar',
       'https://www.punchline.com/wp-json/tribe/events/v1/events',
       0, true, '{}'::jsonb
FROM clubs c
WHERE (c.name = 'The Punchline Comedy Club' OR c.google_place_id = 'ChIJhzE5oJcO9YgRE5wQsfexfqw')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'the_events_calendar'
  );
