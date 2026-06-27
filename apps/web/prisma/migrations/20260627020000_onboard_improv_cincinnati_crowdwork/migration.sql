-- Onboard Improv Cincinnati at Clifton Comedy Theatre (Cincinnati, OH) — TASK-3344,
-- objective #10 discover-comedy-venues near Cincinnati 45202.
--
-- Improv Cincinnati (improvcincinnati.com) is a fixed comedy theatre at 404 Ludlow
-- Ave (Clifton Comedy Theatre). The discovery hint said "ShowClix / Leap
-- (events.leapevents.com)", but that is UNVERIFIED and wrong: the site's shows are
-- hydrated by **Crowdwork** — the same platform the existing `crowdwork` scraper
-- already handles — via the API at crowdwork.com/api/v2/improvcincinnati/shows.
--
-- Wrinkle: that one Crowdwork feed is the umbrella Improv Cincinnati slate (~18
-- comedy shows: Late Night Snack, STACKED, improv jams, ComedySportz, etc.). The
-- ComedySportz brand is already onboarded as a SEPARATE club (TASK-3343,
-- "ComedySportz Cincinnati" club 11444) pointing at the same feed with
-- include_title_patterns=[comedysportz,csz]. To onboard the REST of the Improv
-- Cincinnati slate here WITHOUT double-counting CSz, this source points at the
-- same feed with `exclude_title_patterns`=[comedysportz,csz] — the mirror image of
-- the sibling club's include filter. Exclude wins over include in the scraper, so
-- the two clubs partition the feed cleanly.
--
-- The Crowdwork API returns Rails-style timezone names ("Eastern Time (US &
-- Canada)"), so rails_to_iana=true maps them to America/New_York.
--
-- Fixed VENUE (its own Google place + website) -> visible=true.
--
-- Verification: validated end-to-end against the LIVE Crowdwork API — the exclude
-- filter drops the recurring "ComedySportz Matinee" (owned by club 11444), leaving
-- the 17 non-CSz Improv Cincinnati shows for this club.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible). Guard on name OR google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Improv Cincinnati at Clifton Comedy Theatre',
       '404 Ludlow Ave, Cincinnati, OH 45220',
       'http://www.improvcincinnati.com',
       'Cincinnati', 'OH', '45220',
       'America/New_York', 'US', 'club',
       'ChIJvQ3yUZK0QYgR_tWt0c55zl0',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'Improv Cincinnati at Clifton Comedy Theatre'
     OR google_place_id = 'ChIJvQ3yUZK0QYgR_tWt0c55zl0'
);

-- 2. The crowdwork scraping source (the `/shows` feed + ComedySportz-exclude
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
         'exclude_title_patterns', jsonb_build_array('comedysportz', 'csz')
       )
FROM clubs c
WHERE (c.name = 'Improv Cincinnati at Clifton Comedy Theatre' OR c.google_place_id = 'ChIJvQ3yUZK0QYgR_tWt0c55zl0')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'crowdwork'
  );
