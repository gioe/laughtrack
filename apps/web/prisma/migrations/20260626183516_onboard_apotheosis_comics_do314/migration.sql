-- Onboard Apotheosis Comics and Lounge (St. Louis, MO) — TASK-3307,
-- objective #7 discover-comedy-venues near St. Louis 63101.
--
-- Apotheosis Comics and Lounge (shopapotheosis.com — a Shopify comic shop) is a
-- comic bookstore & lounge that also hosts a recurring stand-up comedy series
-- (Apotheosis Comedy Showcase / South City Comedy Showcase). Its own Shopify
-- site has no live event feed of its own: the "theshopcalendar.com" widget on
-- its /pages/calendar is inactive ("Your calendar is not active"), and comedy
-- tickets/listings run through do314 (the St. Louis DoStuff Media city site).
--
-- do314 exposes a clean per-venue JSON feed shared across the whole DoStuff
-- network (do312, do617, doLA, …):
--   GET https://do314.com/venues/<slug>/events.json
--   -> {"venue": {...}, "event_groups": [{"date", "events": [...]}], ...}
-- This onboards the venue on the net-new generic `do314` scraper (scraper_key
-- = 'do314'), which flattens event_groups and — because Apotheosis is a
-- mixed-use comic shop — keeps only do314's own category_param == 'comedy'
-- events by default (override per source via metadata do314_include_all_categories
-- / do314_categories).
--
-- Fixed VENUE (its own venue) -> visible=true. metadata '{}' = default
-- comedy-only filter.
--
-- Verification: the `do314` scraper was validated end-to-end against the LIVE
-- do314 API — 25 shows off the-old-rock-house (all categories) and 2 comedy
-- shows off the-improv-shop (comedy filter) — plus a recorded-fixture unit
-- suite. This venue currently has 0 upcoming events on do314 (event_groups: [],
-- the 2025 comedy showcases are past), so a scrape returns 0 today; the nightly
-- run will populate it when the next showcase is posted. 0 here is the genuine
-- current state, not a scraper failure.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible).
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Apotheosis Comics and Lounge',
       '3206 S Grand Blvd',
       'https://shopapotheosis.com/',
       'St. Louis', 'MO', '63118',
       'America/Chicago', 'US', 'club',
       'ChIJ8f8Xmk-02IcRR-YUfeXL80g',
       true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Apotheosis Comics and Lounge');

-- 2. The do314 scraping source (events.json feed for this venue).
-- platform is the curated `ScrapingPlatform` enum; do314 is not a member, so use
-- the 'custom' catch-all (as json_ld / ludus / tock / improv sources do). The
-- scraper is resolved by scraper_key ('do314'), not by platform.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom', 'do314',
       'https://do314.com/venues/apotheosis-comics-and-lounge/events.json',
       0, true, '{}'::jsonb
FROM clubs c
WHERE c.name = 'Apotheosis Comics and Lounge'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'do314'
  );
