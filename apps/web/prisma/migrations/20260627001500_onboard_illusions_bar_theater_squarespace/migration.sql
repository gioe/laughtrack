-- Onboard Illusions Bar & Theater (Baltimore, MD) — TASK-3337,
-- objective #9 discover-comedy-venues near Baltimore 21201.
--
-- Illusions Bar & Theater (illusionsmagicbar.com) is a Federal Hill comedy-magic
-- theater (sleight-of-hand / mentalism + comedy; NOT the Illusions drag-show
-- franchise). Its own Squarespace site exposes an Events collection
-- (typeName='events', collectionId 5dcdd5d157c3895774d28edb) backing /events,
-- /tickets and /calendar, so the existing generic `squarespace` scraper handles
-- it via the GetItemsByMonth bulk API.
--
-- The collection mixes the recurring public show ("Mischief & Deception Comedy
-- Magic Show") with venue blackout markers ("CLOSED FOR PRIVATE EVENT"), so the
-- source uses the squarespace scraper's `exclude_title_patterns` metadata filter
-- to drop the private-event placeholders while keeping every real show. (Exclude
-- rather than an allowlist so future differently-named comedy-magic shows are
-- not accidentally dropped.)
--
-- Fixed VENUE (its own theater) -> visible=true. The Squarespace bulk API does
-- not carry ticket price, so shows persist with a fallback ticket (price null) —
-- a real access record, expected for this datasource.
--
-- Verification: validated end-to-end against the LIVE Squarespace API — 21 shows
-- scraped/persisted (the 3 "CLOSED FOR PRIVATE EVENT" placeholders dropped by the
-- filter), dates through 2026-08.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible). Guard on name OR google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Illusions Bar & Theater',
       '1025 S Charles St',
       'https://www.illusionsmagicbar.com/',
       'Baltimore', 'MD', '21230',
       'America/New_York', 'US', 'club',
       'ChIJgS3GnWgDyIkR3bX26JPsEOY',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'Illusions Bar & Theater'
     OR google_place_id = 'ChIJgS3GnWgDyIkR3bX26JPsEOY'
);

-- 2. The squarespace scraping source (Events-collection GetItemsByMonth API +
-- private-event exclude filter). platform 'squarespace' is a curated enum value.
-- jsonb_build_object keeps the metadata quoting clean. Locate the club by name OR
-- google_place_id for idempotency parity with the guard above.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'squarespace', 'squarespace',
       'https://www.illusionsmagicbar.com/api/open/GetItemsByMonth?collectionId=5dcdd5d157c3895774d28edb',
       0, true,
       jsonb_build_object(
         'exclude_title_patterns',
         jsonb_build_array('closed for private', 'private event')
       )
FROM clubs c
WHERE (c.name = 'Illusions Bar & Theater' OR c.google_place_id = 'ChIJgS3GnWgDyIkR3bX26JPsEOY')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'squarespace'
  );
