-- Onboard two downtown-Boston comedy venues discovered via discover-comedy-venues
-- near ZIP 02101 (resolved via 02108) - TASK-3151.
--
-- These are the two clean wins from the closest Boston cluster; the other three
-- cluster venues (Jacques' Cabaret = Timely, needs a net-new scraper; Glovebox =
-- organizer mismatch / dormant; The Point = roving multi-venue promoters) were
-- deferred to follow-up tasks after live datasource investigation.
--
-- 1. Lil Chuck Boston (74 Warrenton St, Boston, MA 02116) — 199-seat comedy
--    theater. Its own site (lilchuckboston.com) links straight to the Tixr
--    storefront tixr.com/groups/lilchuckboston (numeric group_id 2628). Tixr is
--    DataDome-gated, so metadata mirrors the existing proxy/fallback pattern
--    (datadome_dependent + tixr_group_events_api_fallback). Verified 2026-06-21:
--    a real scrape persisted 2 shows (Dr. Kojo Sarfo, Comedic Cody Smith) for
--    club 10942 via the group-events-API fallback.
--
-- 2. The White Bull Tavern (1 Union St, Boston, MA 02108) — Faneuil Hall bar
--    whose own /page/comedy links directly to the Hideout Comedy Eventbrite
--    organizer (id 26813798849). Every event on that organizer is at the White
--    Bull, so it is wired as a single-venue club datasource. Verified 2026-06-21:
--    a real scrape persisted 26 shows for club 10943.

-- ---- Lil Chuck Boston (Tixr) ----
INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Lil Chuck Boston', '74 Warrenton St', 'https://lilchuckboston.com/',
    'Boston', 'MA', '02116', 'America/New_York', 'US', 'club',
    'ChIJqyrhpz9744kRrX1swGAeQW4', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJqyrhpz9744kRrX1swGAeQW4'
       OR name = 'Lil Chuck Boston'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'tixr'::"ScrapingPlatform",
    'tixr',
    'https://www.tixr.com/groups/lilchuckboston',
    TRUE,
    0,
    '{"tixr_group_id":"2628","tixr_source_type":"detail_page","datadome_dependent":true,"detail_fetch_required":true,"tixr_group_events_api_fallback":true}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJqyrhpz9744kRrX1swGAeQW4' OR c.name = 'Lil Chuck Boston')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'tixr'
  );

-- ---- The White Bull Tavern (Eventbrite / Hideout Comedy) ----
INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'The White Bull Tavern', '1 Union St', 'https://thewhitebulltavern.com/',
    'Boston', 'MA', '02108', 'America/New_York', 'US', 'club',
    'ChIJcZwr74Vw44kRJcaBYDUpFOE', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJcZwr74Vw44kRJcaBYDUpFOE'
       OR name = 'The White Bull Tavern'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com/o/26813798849',
    '26813798849',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJcZwr74Vw44kRJcaBYDUpFOE' OR c.name = 'The White Bull Tavern')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite'
  );
