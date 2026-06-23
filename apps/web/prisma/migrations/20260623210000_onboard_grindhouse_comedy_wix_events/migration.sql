-- Onboard Grindhouse Comedy (Sacramento, CA) via the existing wix_events scraper - TASK-3202.
--
-- Grindhouse Comedy is a Sacramento-based stand-up comedy promoter that books
-- touring stand-ups (Billy Wayne Davis, Eddie Pepitone, etc.). Its site
-- (https://www.grindhousecomedy.com/) is built on Wix and uses the native
-- Wix Events app for its show listings (/events and /event-list pages).
--
-- Datasource (verified 2026-06-23): the Wix Events viewer API
--   {domain}/_api/wix-one-events-server/web/paginated-events/viewer
-- returns this site's events without a compId (the schedule-page case the
-- generic wix_events scraper already supports), so wix_event_id is left NULL
-- and the scraper fetches all events from the site root.
--
-- The Wix Events transformer attributes every event to this single club
-- (it does not split per-event location into separate venue clubs), so
-- Grindhouse is onboarded as a VISIBLE Sacramento club at its own listed
-- address / Google comedy_club listing (place_id below), mirroring how other
-- Wix-native single-club venues (Bushwick, AC Jokes) are wired.
--
-- VERIFICATION NOTE (2026-06-23): the API + scraper wiring works, but the
-- promoter is currently DORMANT — the only events the API returns are 8 PAST
-- shows (newest 2025-03-15), with zero upcoming. A real scrape today persists 0
-- shows because there are no future events to surface, NOT because of a scraper
-- gap. The enabled scraping_sources row means the scraper will automatically
-- pick up shows the moment Grindhouse posts new Wix events.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Grindhouse Comedy', '1819 E St, Sacramento, CA 95811, USA',
    'https://www.grindhousecomedy.com/',
    'Sacramento', 'CA', '95811', 'America/Los_Angeles', 'US', 'club',
    'ChIJz3JsGlbXmoARq6URvJkg0gc', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJz3JsGlbXmoARq6URvJkg0gc'
       OR name = 'Grindhouse Comedy'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, wix_event_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'wix_events'::"ScrapingPlatform",
    'wix_events',
    'https://www.grindhousecomedy.com',
    NULL,
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJz3JsGlbXmoARq6URvJkg0gc' OR c.name = 'Grindhouse Comedy')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'wix_events'
  );
