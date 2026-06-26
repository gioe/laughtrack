-- Onboard Warren Station Center for the Arts at Keystone (Keystone, CO) —
-- TASK-3430 (discover-comedy-venues near 80202).
--
-- Warren Station is a fixed mountain-town arts center in River Run Village below
-- Keystone Resort (164 Ida Belle Dr). Its own WordPress site (warrenstation.com)
-- runs The Events Calendar (Tribe) plugin and exposes the public REST feed at
--   https://warrenstation.com/wp-json/tribe/events/v1/events
-- so it maps to the existing GENERIC `the_events_calendar` scraper — no new code.
--
-- It is a mixed-use venue: the calendar mostly carries concerts, festivals, yoga,
-- wine/food events, etc., alongside a genuine recurring stand-up series
-- ("Winter Comedy Series" / "Summer Comedy Series", booked in partnership with
-- Comedy Works Denver — e.g. Summer Comedy Series: Dean Stanfield 2026-07-10,
-- Zavior Phillips 2026-08-15). There is no native "Comedy" Tribe category (comedy
-- events sit under the generic "Warren Station Event" category), so the source
-- carries an opt-in `include_title_patterns` comedy allowlist to keep only the
-- stand-up shows (the filter is OFF by default for pure-comedy Tribe sources).
-- Verified: a real scrape produced 2 upcoming comedy shows (the title filter
-- dropped ~38 non-comedy rows).
--
-- Fixed venue (its own room) => visible=true.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Venue club (fixed venue, visible).
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Warren Station Center for the Arts at Keystone',
       '164 Ida Belle Dr',
       'https://warrenstation.com',
       'Keystone', 'CO', '80435', 'America/Denver', 'US', 'club',
       'ChIJEcCDlTRXaocRNYJTdrgb1V4', true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Warren Station Center for the Arts at Keystone');

-- 2. The Events Calendar (Tribe) scraping source (no unique constraint beyond PK,
--    so guard with NOT EXISTS on (club_id, scraper_key)). source_url = the Tribe
--    REST feed; include_title_patterns keeps only the comedy series.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'tribe_events', 'the_events_calendar',
       'https://warrenstation.com/wp-json/tribe/events/v1/events', 0, true,
       '{"include_title_patterns": ["comedy", "comedian", "stand[ -]?up"]}'::jsonb
FROM clubs c
WHERE c.name = 'Warren Station Center for the Arts at Keystone'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'the_events_calendar'
  );
