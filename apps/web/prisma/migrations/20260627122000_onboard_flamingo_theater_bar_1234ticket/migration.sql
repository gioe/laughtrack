-- Onboard Flamingo Theater Bar (Miami, FL) — TASK-3350,
-- objective #14 discover-comedy-venues near Miami 33130.
--
-- Flamingo Theater Bar is a ~350-cap Brickell venue ticketed through the
-- 1234ticket platform. Its events are served by the public, unauthenticated feed
--   https://api.1234ticket.com/api_040/landing-data
-- which returns EVERY event across the platform's venues (Flamingo + La Scala de
-- Miami) with no event category. This ships a NEW generic `1234ticket` scraper
-- (apps/scraper/.../scrapers/implementations/api/ticket1234/) that:
--   1. filters the platform-wide feed to this venue by `metadata.venue_id` (UUID); and
--   2. applies an opt-in `include_title_patterns` comedy allowlist (matched
--      against title + description + de-hyphenated link slug), because the venue
--      mixes stand-up comedy with Latin music/dance concerts and the API exposes
--      no category to separate them.
-- (The newer live.1234ticket.com Next.js storefront uses a token-gated api-live
-- v2 API that 403s anonymously; the scraper deliberately uses api_040.)
--
-- Fixed VENUE -> visible=true. timezone America/New_York drives the date+time ->
-- UTC combination the scraper performs.
--
-- Verification: validated end-to-end against the LIVE 1234ticket API — the
-- comedy allowlist isolated 3 comedy shows (Eddy Suarez, Alexis Valdes, George
-- Harris) from 18 platform events. Caveat: the recurring "El Show De George
-- Harris" ("todos los jueves") carries a single far-future placeholder date/time
-- in the source, so it persists with a wrong one-off datetime — a source-data
-- limitation, not a scraper bug.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible). Guard on name OR google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Flamingo Theater Bar',
       '905 Brickell Bay Dr, Miami, FL 33131',
       'https://live.1234ticket.com/venues/1',
       'Miami', 'FL', '33131',
       'America/New_York', 'US', 'club',
       'ChIJx-nDQoK22YgRJYLsQ1PEaKY',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'Flamingo Theater Bar'
     OR google_place_id = 'ChIJx-nDQoK22YgRJYLsQ1PEaKY'
);

-- 2. The 1234ticket scraping source. platform 'custom' (1234ticket is not a
-- ScrapingPlatform enum member; the scraper is resolved by scraper_key).
-- metadata: venue UUID filter + comedy include allowlist. jsonb_build_object
-- keeps the metadata quoting clean. Locate the club by name OR google_place_id.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom', '1234ticket',
       'https://api.1234ticket.com/api_040/landing-data',
       0, true,
       jsonb_build_object(
         'venue_id', '6853052c-f82a-4e10-9171-3f88889bf2df',
         'include_title_patterns',
         jsonb_build_array('comedy', 'comedian', 'stand up', 'standup', 'stand-up',
                           'humor', 'comico', 'cómico', 'george harris',
                           'eddy suarez', 'alexis valdes')
       )
FROM clubs c
WHERE (c.name = 'Flamingo Theater Bar' OR c.google_place_id = 'ChIJx-nDQoK22YgRJYLsQ1PEaKY')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = '1234ticket'
  );
