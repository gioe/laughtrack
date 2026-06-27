-- Onboard Boca Black Box Center for the Arts (Boca Raton, FL) — TASK-3358,
-- objective #11 discover-comedy-venues near Miami 33130.
--
-- Boca Black Box is a mixed-use performing-arts center: most of its calendar is
-- tribute bands, concerts, youth theatre, movies, magic, and wrestling, but it
-- runs a steady stand-up program in its adjacent "The Box 2.0" room (recurring
-- "Comedian <name>" bookings, Have-Nots Comedy Show, Noches De Comedia, Boomer
-- Humor Comedy Tour, etc.). Ticketing is accesso ShoWare at
--   https://bocablackbox.showare.com/
-- The existing generic `showare` scraper handles it (derives the
-- /include/widgets/events/performancelist.asp JSON endpoint from the host).
--
-- Wrinkle: the ShoWare performance list has no category, so a comedy
-- `include_title_patterns` allowlist (case-insensitive substrings matched on the
-- event title) keeps only the stand-up. 'comedia' substring-matches both
-- 'Comedian'/'Comediante' and 'Noches De Comedia'; 'comedy' + 'comic' cover the
-- rest. The music/movie/tribute/wrestling programming has no comedy keyword and
-- is dropped.
--
-- Fixed VENUE -> visible=true.
--
-- Verification: validated end-to-end against the LIVE ShoWare feed and prod DB —
-- the allowlist isolated 23 distinct comedy events (40 performances) from the
-- venue's 54 non-comedy events, with zero non-comedy leakage (club 11457,
-- source 7025). More surface as the scrape window rolls forward nightly.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible). Guard on name OR google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Boca Black Box Center for the Arts',
       '8221 Glades Rd Ste 10, Boca Raton, FL 33434',
       'https://www.bocablackbox.com/',
       'Boca Raton', 'FL', '33434',
       'America/New_York', 'US', 'club',
       'ChIJiTAJXqYe2YgR-gLA4AorAU8',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'Boca Black Box Center for the Arts'
     OR google_place_id = 'ChIJiTAJXqYe2YgR-gLA4AorAU8'
);

-- 2. The showare scraping source (ShoWare host + comedy include allowlist).
-- jsonb_build_object keeps the metadata quoting clean. Locate the club by name
-- OR google_place_id for idempotency parity with the guard above.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom', 'showare',
       'https://bocablackbox.showare.com/default.asp',
       0, true,
       jsonb_build_object(
         'include_title_patterns',
         jsonb_build_array('comedy', 'comedia', 'comic')
       )
FROM clubs c
WHERE (c.name = 'Boca Black Box Center for the Arts' OR c.google_place_id = 'ChIJiTAJXqYe2YgR-gLA4AorAU8')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'showare'
  );
