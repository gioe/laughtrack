-- Onboard Provocation Theatre (Berkeley, CA) via generic Wix Events scraper - TASK-3186.
--
-- The venue is a dedicated improv/comedy theater at 2177 Bancroft Way. Its Wix
-- Events widget (component comp-mlh8cqwc) returned 6 upcoming ticketed comedy /
-- improv events on 2026-06-23, including Intergalactic Collision, Zodiac Nights,
-- Super Bros. Sunday, and Press Start. All are native Wix Events with ticketing.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Provocation Theatre',
    '2177 Bancroft Way',
    'https://www.provocationtheatre.com/',
    'Berkeley',
    'CA',
    '94704',
    'America/Los_Angeles',
    'US',
    'club',
    'ChIJe9TOGix8hYARnzexd5UJ9gs',
    TRUE,
    'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJe9TOGix8hYARnzexd5UJ9gs'
       OR name = 'Provocation Theatre'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, wix_event_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'wix_events'::"ScrapingPlatform",
    'wix_events',
    'https://www.provocationtheatre.com',
    'comp-mlh8cqwc',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJe9TOGix8hYARnzexd5UJ9gs' OR c.name = 'Provocation Theatre')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'wix_events'::"ScrapingPlatform"
        AND s.priority = 0
  );
