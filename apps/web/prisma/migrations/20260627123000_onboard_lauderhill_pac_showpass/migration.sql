-- Onboard Lauderhill Performing Arts Center (Lauderhill, FL) — TASK-3355,
-- objective #14 discover-comedy-venues near Miami 33130.
--
-- LPAC is a municipal performing-arts center whose calendar is powered by
-- Showpass. Its events are served by the public Showpass calendar API
--   https://www.showpass.com/api/public/venues/lauderhill-performing-arts-center-lpac/calendar/
-- (venue slug found via a showpass.com event page; the venue's own lpacfl.com is
-- Akamai-bot-protected). The existing generic `showpass` scraper handles it.
--
-- Wrinkle: the venue mixes recurring stand-up (Lauderhill Live comedy series,
-- Funny Women) with plays, ballet, and cultural events, and the Showpass API has
-- NO event category. TASK-3355 added an opt-in `include_title_patterns` comedy
-- allowlist (case-insensitive substrings matched on the event name) to the
-- showpass scraper; this source uses it to keep only the comedy programming.
--
-- Fixed VENUE -> visible=true.
--
-- Verification: validated end-to-end against the LIVE Showpass API — the comedy
-- allowlist isolated the recurring "Lauderhill Live" comedy show from the
-- venue's ballet/plays/cultural events (1 comedy show in the scraper's 3-month
-- window; more surface as the window rolls forward nightly).
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible). Guard on name OR google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Lauderhill Performing Arts Center',
       '3800 NW 11th Pl, Lauderhill, FL 33311',
       'https://www.lpacfl.com/',
       'Lauderhill', 'FL', '33311',
       'America/New_York', 'US', 'club',
       'ChIJfag92OYG2YgRP5Oibm9GnAg',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'Lauderhill Performing Arts Center'
     OR google_place_id = 'ChIJfag92OYG2YgRP5Oibm9GnAg'
);

-- 2. The showpass scraping source (venue calendar API + comedy include
-- allowlist). jsonb_build_object keeps the metadata quoting clean. Locate the
-- club by name OR google_place_id for idempotency parity with the guard above.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'showpass', 'showpass',
       'https://www.showpass.com/api/public/venues/lauderhill-performing-arts-center-lpac/calendar/',
       0, true,
       jsonb_build_object(
         'include_title_patterns',
         jsonb_build_array('lauderhill live', 'comedy', 'comedian', 'stand up',
                           'standup', 'stand-up', 'funny', 'comic')
       )
FROM clubs c
WHERE (c.name = 'Lauderhill Performing Arts Center' OR c.google_place_id = 'ChIJfag92OYG2YgRP5Oibm9GnAg')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'showpass'
  );
