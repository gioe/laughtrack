-- Onboard ComedySportz Cincinnati (Cincinnati, OH) — TASK-3343,
-- objective #10 discover-comedy-venues near Cincinnati 45202.
--
-- ComedySportz Cincinnati (cszcincinnati.com) is the CSz-branded programming of
-- Improv Cincinnati. The discovery hint said "Eventbrite", but the site's "GET
-- TICKETS" link points at **Crowdwork** (crowdwork.com/v/improvcincinnati/...) —
-- the same platform the existing `crowdwork` scraper already handles. The shows
-- are hydrated by the Crowdwork API at crowdwork.com/api/v2/improvcincinnati/shows.
--
-- Wrinkle: that one Crowdwork feed is the umbrella Improv Cincinnati slate (~18
-- comedy shows: ComedySportz, Late Night Snack, STACKED, improv jams, etc.). The
-- broader Improv Cincinnati programming is a SEPARATE onboarding task (TASK-3344,
-- "Improv Cincinnati at Clifton Comedy Theatre"). To keep THIS club scoped to the
-- ComedySportz brand, the source uses the crowdwork scraper's
-- `include_title_patterns` metadata filter to keep only ComedySportz-titled shows
-- (e.g. "ComedySportz Matinee"), leaving the rest of the slate for TASK-3344.
--
-- The Crowdwork API returns Rails-style timezone names ("Eastern Time (US &
-- Canada)"), so rails_to_iana=true maps them to America/New_York.
--
-- Fixed VENUE brand (its own Google place + website) -> visible=true.
--
-- Verification: validated end-to-end against the LIVE Crowdwork API — the
-- include filter drops the 17 non-CSz Improv Cincinnati shows, leaving the
-- recurring "ComedySportz Matinee" (1 upcoming show persisted, date converted
-- 14:00 EDT -> 18:00 UTC correctly).
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible). Guard on name OR google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'ComedySportz Cincinnati',
       '3064 Harrison Ave, Cincinnati, OH 45211',
       'https://www.cszcincinnati.com',
       'Cincinnati', 'OH', '45211',
       'America/New_York', 'US', 'club',
       'ChIJB4Nq55m1QYgRqyw_vcEzirI',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'ComedySportz Cincinnati'
     OR google_place_id = 'ChIJB4Nq55m1QYgRqyw_vcEzirI'
);

-- 2. The crowdwork scraping source (the `/shows` feed + ComedySportz-include
-- title filter). platform 'crowdwork' is a curated enum value; the scraper is
-- resolved by scraper_key. jsonb_build_object keeps the metadata quoting clean.
-- Locate the club by name OR google_place_id for idempotency parity with the
-- guard above.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'crowdwork', 'crowdwork',
       'https://crowdwork.com/api/v2/improvcincinnati/shows',
       0, true,
       jsonb_build_object(
         'rails_to_iana', true,
         'default_timezone', 'America/New_York',
         'include_title_patterns', jsonb_build_array('comedysportz', 'csz')
       )
FROM clubs c
WHERE (c.name = 'ComedySportz Cincinnati' OR c.google_place_id = 'ChIJB4Nq55m1QYgRqyw_vcEzirI')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'crowdwork'
  );
