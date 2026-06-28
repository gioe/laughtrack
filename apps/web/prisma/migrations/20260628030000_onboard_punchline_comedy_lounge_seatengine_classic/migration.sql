-- Onboard Punchline Comedy Lounge (Southfield, MI) — TASK-3376,
-- objective #12 discover-comedy-venues near Detroit 48226.
--
-- Punchline Comedy Lounge is a fixed Southfield comedy club with a recurring
-- weekly stand-up calendar (anniversary showcases, hosted nights, touring
-- comedians: LaLa Love, Coco, 404 Blac, Comedian CP, J-Will, ...). Its own site
-- (comedypunchline.com) is a SeatEngine-hosted white-label calendar — the page
-- is served with cdn.seatengine.com/assets/application scripts and a
-- files.seatengine.com/styles/logos/316 logo, the Classic-platform signal
-- (SCRAPERS.md SeatEngine Identification Checklist). The 19 live events are all
-- comedy, so no comedy_filter is needed.
--
-- Wiring — seatengine_classic. The Classic scraper fetches the venue calendar
-- directly from scraping_url=https://www.comedypunchline.com/events (the same
-- /events path every other classic venue uses, e.g. bricktowncomedy.com/events).
-- seatengine_id is NOT used at runtime for classic venues (it only appears for
-- record-keeping) and the CDN logo id 316 is a file-storage id in a different
-- namespace than the API venue id, so it is intentionally left NULL here per
-- the SCRAPERS.md warning. Fixed venue -> visible=true.
--
-- Verification: a seatengine_classic scrape of https://www.comedypunchline.com/events
-- returned 19 comedy shows, each show_page_url a comedypunchline.com/shows/<id>
-- page; a real `make scrape-club-id ID=<club_id>` persisted them onto this club.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible). Guard on name OR google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Punchline Comedy Lounge',
       '29555 Northwestern Hwy #312, Southfield, MI 48034',
       'https://www.comedypunchline.com',
       'Southfield', 'MI', '48034',
       'America/Detroit', 'US', 'club',
       'ChIJv_54_XO3JIgRq34ml241Yk4',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'Punchline Comedy Lounge'
     OR google_place_id = 'ChIJv_54_XO3JIgRq34ml241Yk4'
);

-- 2. The seatengine_classic scraping source (platform 'seatengine', curated enum;
-- the Classic scraper reads the calendar from source_url at runtime,
-- seatengine_id stays NULL). Locate the club by name OR google_place_id for
-- idempotency.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, seatengine_id, priority, enabled, metadata)
SELECT c.id, 'seatengine', 'seatengine_classic',
       'https://www.comedypunchline.com/events',
       NULL,
       0, true, '{}'::jsonb
FROM clubs c
WHERE (c.name = 'Punchline Comedy Lounge' OR c.google_place_id = 'ChIJv_54_XO3JIgRq34ml241Yk4')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'seatengine_classic'
  );
