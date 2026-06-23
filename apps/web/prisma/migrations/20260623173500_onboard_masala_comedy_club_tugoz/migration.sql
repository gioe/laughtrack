-- Onboard Masala Comedy Club (Sunnyvale, CA) via the new generic Tugoz scraper - TASK-3194.
--
-- Masala's public site confirms stand-up comedy and open mics. Its ticket pages
-- load Tugoz widgets through https://masalacc.org/config.js?v=2, where
-- SITE_CONFIG.LIVE_EVENTS maps page keys to Tugoz static event JSON IDs.
-- Tugoz has no dedicated ScrapingPlatform enum, so this uses platform='custom'
-- with scraper_key='tugoz'.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Masala Comedy Club',
    'Sunnyvale Theatre, Sunnyvale, CA 94087, USA',
    'https://masalacc.org/',
    'Sunnyvale',
    'CA',
    '94087',
    'America/Los_Angeles',
    'US',
    'club',
    'ChIJtQ8e1tm3j4ARjjED59PgP5k',
    TRUE,
    'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJtQ8e1tm3j4ARjjED59PgP5k'
       OR name = 'Masala Comedy Club'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'tugoz',
    'https://masalacc.org/config.js?v=2',
    TRUE,
    0,
    jsonb_build_object(
        'event_keys', jsonb_build_array('openmic', 'lt10'),
        'event_ids', jsonb_build_array(112933, 110095),
        'company_id', 608,
        'host_key', '996a7fa078cc36c46d02f9af3bef918b',
        'site_base', 'https://masalacc.org',
        'notes', 'config.js currently exposes openmic plus stale lt10/Laugh Ticket 9; scraper skips stale past events'
    ),
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJtQ8e1tm3j4ARjjED59PgP5k' OR c.name = 'Masala Comedy Club')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'custom'::"ScrapingPlatform"
        AND s.priority = 0
  );
