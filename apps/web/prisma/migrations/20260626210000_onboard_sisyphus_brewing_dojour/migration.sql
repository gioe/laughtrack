-- Onboard Sisyphus Brewing (Minneapolis, MN) — TASK-3323,
-- objective #8 discover-comedy-venues near Twin Cities 55401.
--
-- Sisyphus Brewing (sisyphusbrewing.com — a Shopify brewery site) runs a
-- dedicated intimate stand-up comedy room with near-nightly programming and a
-- free weekly stand-up open mic. The discovery hint said "Eventbrite", but the
-- brewery's own /pages/events embeds a Dojour calendar iframe
-- (https://dojour.us/embed/u/sisyphusbrewing) — Dojour, not Eventbrite, is what
-- hydrates its listings.
--
-- Dojour (https://dojour.us) is a hosted event/ticketing platform reusable
-- across any venue on it. Its public JSON feed:
--   GET https://dojour.us/api/event_instances/user_feed/
--       ?username=<username>&date_min=<now>&distinct_event=true&exclude_plans=true
-- returns events whose `upcoming_showing_set` lists every upcoming showtime.
-- This onboards the venue on the net-new generic `dojour` scraper (scraper_key
-- = 'dojour'), which parses the username from source_url, follows pagination,
-- and expands each showing into its own Show. No category filter is applied:
-- Dojour exposes no reliable per-event comedy tag and this is a dedicated
-- comedy room (its Dojour calendar IS the comedy room's calendar).
--
-- Fixed VENUE (its own venue) -> visible=true. metadata '{}'.
--
-- Verification: validated end-to-end against the LIVE Dojour API — 105 shows
-- scraped, 103 persisted (36 distinct events, dates through 2027-03) — plus a
-- recorded-fixture unit suite.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible).
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Sisyphus Brewing',
       '712 Ontario Ave W #100',
       'https://www.sisyphusbrewing.com/',
       'Minneapolis', 'MN', '55403',
       'America/Chicago', 'US', 'club',
       'ChIJ48UXUOgys1IRmfBmb6NXjh0',
       true, 'active'
-- Guard on the stable google_place_id as well as name, so a re-run can't insert
-- a duplicate if the venue already exists under a slightly different name.
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'Sisyphus Brewing'
     OR google_place_id = 'ChIJ48UXUOgys1IRmfBmb6NXjh0'
);

-- 2. The dojour scraping source (Dojour embed URL for this venue).
-- platform is the curated `ScrapingPlatform` enum; dojour is not a member, so
-- use the 'custom' catch-all (as json_ld / do314 / ical / tock sources do). The
-- scraper is resolved by scraper_key ('dojour'), not by platform.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom', 'dojour',
       'https://dojour.us/embed/u/sisyphusbrewing',
       0, true, '{}'::jsonb
-- Locate the club by name OR google_place_id (parity with the clubs guard
-- above) so a fresh-DB venue that already exists under a slightly different
-- name still gets its dojour source wired.
FROM clubs c
WHERE (c.name = 'Sisyphus Brewing' OR c.google_place_id = 'ChIJ48UXUOgys1IRmfBmb6NXjh0')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'dojour'
  );
