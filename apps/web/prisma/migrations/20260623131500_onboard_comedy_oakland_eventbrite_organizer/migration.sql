-- Onboard Comedy Oakland via the Eventbrite organizer scraper - TASK-3182.
--
-- Comedy Oakland is the East Bay's longest-running independent stand-up producer,
-- running 250+ shows/yr across multiple Oakland rooms (Quinn's Lighthouse, Elbo
-- Room Jack London, The Lumpia Company, ...). Its own site (comedyoakland.com)
-- sells every show through Eventbrite, under organizer "Comedy Oakland"
-- (id 836628691).
--
-- Because the producer plays at varying venues, it is modeled as a HIDDEN proxy
-- club (visible = FALSE) wired to the Eventbrite scraper in ORGANIZER mode (the
-- source_url contains "/o/"). The scraper groups the organizer feed by venue and
-- upserts a per-venue club for each; the actual shows surface under those
-- per-venue clubs, not under this proxy. This mirrors existing producer proxies
-- (The Spotlight Comedy, Snowflake Comedy, Henceforth Comedy, Puff Puff Laugh).
--
-- NOTE (verified 2026-06-23): a real scrape fetched 28 live events (all stand-up
-- comedy) and persisted all 28 -- 17 at the auto-created Quinn's Lighthouse club,
-- 10 at Elbo Room Jack London, 1 at The Lumpia Company. The auto-created
-- per-venue clubs are produced by the scraper at runtime and are intentionally
-- NOT inserted here -- only the proxy club + its scraping_sources row are
-- reproducible data.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Comedy Oakland', 'Multiple Locations, Oakland, CA 94607, USA',
    'https://www.comedyoakland.com/',
    'Oakland', 'CA', '94607', 'America/Los_Angeles', 'US', 'club',
    'ChIJ5dQZwLCAj4ARHgyrUSWTEvU', FALSE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJ5dQZwLCAj4ARHgyrUSWTEvU'
       OR name = 'Comedy Oakland'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com/o/comedy-oakland-836628691',
    '836628691',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJ5dQZwLCAj4ARHgyrUSWTEvU' OR c.name = 'Comedy Oakland')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite'
  );
