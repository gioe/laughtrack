-- Onboard Sadman Comedy Cafe (Boca Raton, FL) — TASK-3353,
-- objective #11 discover-comedy-venues near Miami 33130 / Fort Lauderdale 33301.
--
-- "Boca Raton's Premier Comedy Club" — a dedicated comedy brand running recurring
-- stand-up showcases and open mics, all ticketed through its own Eventbrite
-- organizer "Sadman Comedy Cafe, Boca Raton" (id 74684999873). The club's own site
-- (sadmancomedycafe.com) has no structured calendar; Eventbrite is the datasource.
--
-- Datasource: the Eventbrite organizer, wired to the generic `eventbrite` scraper
-- in SINGLE-VENUE mode (conventions #192 / #252): source_url OMITS the /o/ segment
-- and eventbrite_id holds the organizer id. The shows run at MULTIPLE Eventbrite
-- venues (Sol Theatre, the Biergarten) whose names differ from this club's name, so
-- organizer mode would fragment them into several per-venue auto-clubs and bury the
-- Sadman brand. Single-venue mode forces every show onto this one club. The
-- disambiguation probe GET /v3/venues/74684999873/events/ returns 404 (not
-- 200+empty), so the venue->organizer fallback fires safely and all events land
-- (convention #252 silent-zero check passed).
--
-- Fixed comedy brand with a home venue -> visible=true.
--
-- Verified: `make scrape-club-id ID=<club_id>` scraped 4 shows onto the single club
-- (Open Mic at Biergarten + Lisa Corrao / Graduation Showcase / Geno Bisconte at Sol
-- Theatre), with NO duplicate per-venue auto-club created.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Fixed (visible) comedy-brand club. Guard on name OR google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Sadman Comedy Cafe',
       '3333 N Federal Hwy',
       'https://sadmancomedycafe.com',
       'Boca Raton', 'FL', '33431',
       'America/New_York', 'US', 'club',
       'ChIJj2Nnd7Hj2IgR7y2Epno1uaU',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'Sadman Comedy Cafe'
     OR google_place_id = 'ChIJj2Nnd7Hj2IgR7y2Epno1uaU'
);

-- 2. Eventbrite SINGLE-VENUE source: source_url has NO /o/ segment (keeps the
--    scraper out of organizer/per-venue routing); eventbrite_id = organizer id.
--    Guard with NOT EXISTS on (club_id, scraper_key) — no unique constraint beyond
--    the PK.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata)
SELECT c.id, 'eventbrite', 'eventbrite',
       'https://www.eventbrite.com',
       '74684999873', 0, true, '{}'::jsonb
FROM clubs c
WHERE (c.name = 'Sadman Comedy Cafe' OR c.google_place_id = 'ChIJj2Nnd7Hj2IgR7y2Epno1uaU')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'eventbrite'
  );
