-- Onboard Very Good Improv (Minneapolis, MN) — TASK-3330,
-- objective #8 discover-comedy-venues near Twin Cities 55401.
--
-- Very Good Improv is an improv training + performance org. The discovery hint
-- said "Squarespace, no ticket feed / not scrapable", but its /calendar page is
-- hydrated by **Crowdwork** (crowdwork.com/api/v2/verygoodimprov/...) — the same
-- platform the existing `crowdwork` scraper already handles.
--
-- Wrinkle: Crowdwork's clean `/shows` endpoint returns 0 for this venue (it
-- categorizes everything as classes), while the `/all` feed mixes course
-- registrations (Improv 101/201, workshop series) with its genuine public
-- comedy: the recurring Pay-What-You-Want "Very Good Improv Jam!" and occasional
-- student showcases. So we point source_url at `/all` and use the crowdwork
-- scraper's new `exclude_title_patterns` metadata filter (TASK-3330) to drop the
-- class/workshop items by title, keeping only the public shows.
--
-- Fixed VENUE (performs at Phoenix Theater, its listed address) -> visible=true.
--
-- Verification: validated end-to-end against the LIVE Crowdwork API — the filter
-- drops the Improv 101/201 classes and the paid workshop series, leaving the
-- recurring "Very Good Improv Jam!" (2 upcoming shows persisted; the prior
-- unfiltered rows were reconciled away).
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible). Guard on name OR google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Very Good Improv',
       '2605 Hennepin Ave, Minneapolis, MN 55408 (Phoenix Theater)',
       'https://www.verygoodimprov.com/',
       'Minneapolis', 'MN', '55408',
       'America/Chicago', 'US', 'club',
       'ChIJPVhq_CYzs1IR6XIZkRC-pno',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'Very Good Improv'
     OR google_place_id = 'ChIJPVhq_CYzs1IR6XIZkRC-pno'
);

-- 2. The crowdwork scraping source (the `/all` feed + class-exclude title filter).
-- platform 'crowdwork' is a curated enum value; the scraper is resolved by
-- scraper_key. jsonb_build_object keeps the metadata quoting clean. Locate the
-- club by name OR google_place_id for idempotency parity with the guard above.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'crowdwork', 'crowdwork',
       'https://crowdwork.com/api/v2/verygoodimprov/all',
       0, true,
       jsonb_build_object(
         'exclude_title_patterns',
         jsonb_build_array('improv 1', 'improv 2', 'improv 3', 'workshop', 'class', 'intensive', 'series')
       )
FROM clubs c
WHERE (c.name = 'Very Good Improv' OR c.google_place_id = 'ChIJPVhq_CYzs1IR6XIZkRC-pno')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'crowdwork'
  );
