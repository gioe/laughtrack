-- Onboard Commonwealth Comedy Club (Dayton, KY) — TASK-3345,
-- objective #10 discover-comedy-venues near Cincinnati 45202/41011.
--
-- Independent stand-up club in a converted church with a full rotating SimpleTix
-- calendar. Its site (commonwealthcomedyclub.com) links to a SimpleTix organizer
-- page (commonwealthcomedyclub.simpletix.com) listing ~47 one-off comedian
-- bookings, each on its own /e/...-tickets-{id} event page.
--
-- Handled by the existing `simpletix` scraper, extended in this task (TASK-3345)
-- with TWO enhancements so it fits a multi-event organizer (not just a single
-- recurring show):
--   1. collect_scraping_targets() enumerates the organizer page's /e/ event
--      links when source_url is a `{org}.simpletix.com` listing (no /e/ path).
--   2. get_data() falls back to JSON-LD `Event` data when a page has no inline
--      `var timeArray` — these single-date bookings carry only JSON-LD. The
--      JSON-LD UTC startDate is converted to the venue's local wall-clock to
--      match the timeArray persistence convention.
-- Existing single-event simpletix rows (www.simpletix.com/e/...) are unaffected:
-- the listing branch only fires for the organizer-subdomain URL shape.
--
-- Fixed VENUE (its own address) -> visible=true. SimpleTix returns UTC instants;
-- timezone America/New_York drives the wall-clock conversion.
--
-- Verification: validated end-to-end against the LIVE SimpleTix organizer page —
-- 47 events enumerated, 98 shows persisted (e.g. MAX FINE 7:30 & 9:45 PM ET).
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible). Guard on name OR google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Commonwealth Comedy Club',
       '522 5th Ave, Dayton, KY 41074',
       'https://www.commonwealthcomedyclub.com',
       'Dayton', 'KY', '41074',
       'America/New_York', 'US', 'club',
       'ChIJb9SPLKSzQYgRy7HomEyaDHI',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'Commonwealth Comedy Club'
     OR google_place_id = 'ChIJb9SPLKSzQYgRy7HomEyaDHI'
);

-- 2. The simpletix scraping source. platform 'simpletix' is a curated enum
-- value; the scraper is resolved by scraper_key. source_url is the organizer
-- listing page (the scraper enumerates its per-event links). Locate the club by
-- name OR google_place_id for idempotency parity with the guard above.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'simpletix', 'simpletix',
       'https://commonwealthcomedyclub.simpletix.com/',
       0, true, '{}'::jsonb
FROM clubs c
WHERE (c.name = 'Commonwealth Comedy Club' OR c.google_place_id = 'ChIJb9SPLKSzQYgRy7HomEyaDHI')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'simpletix'
  );
