-- TASK-3021: Onboard Comedy Plex Comedy Club.
--
-- Comedy Plex runs Odoo website_event. Event listing pages link to native
-- /event/<slug>/register detail pages, which expose schema.org Event
-- microdata parsed by scraper_key='odoo_events'.

INSERT INTO clubs (
    name,
    address,
    website,
    zip_code,
    timezone,
    visible,
    city,
    state,
    status,
    club_type,
    google_place_id
)
SELECT
    'Comedy Plex Comedy Club',
    '1128 Lake St Lower Level',
    'https://www.comedyplex.com/',
    '60301',
    'America/Chicago',
    TRUE,
    'Oak Park',
    'IL',
    'active',
    'club',
    'ChIJay-qo0o1DogRX4A3IKWe2ek'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJay-qo0o1DogRX4A3IKWe2ek'
        OR lower(name) = lower('Comedy Plex Comedy Club')
);

UPDATE clubs
   SET address = '1128 Lake St Lower Level',
       website = 'https://www.comedyplex.com/',
       zip_code = '60301',
       timezone = 'America/Chicago',
       visible = TRUE,
       city = 'Oak Park',
       state = 'IL',
       status = 'active',
       club_type = 'club',
       google_place_id = COALESCE(google_place_id, 'ChIJay-qo0o1DogRX4A3IKWe2ek')
 WHERE google_place_id = 'ChIJay-qo0o1DogRX4A3IKWe2ek'
    OR lower(name) = lower('Comedy Plex Comedy Club');

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    priority,
    enabled,
    metadata
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'odoo_events',
    'https://www.comedyplex.com/event',
    0,
    TRUE,
    '{"exclude_title_patterns":["\\bclass(?:es)?\\b","\\bworkshop(?:s)?\\b","\\bcamp(?:s)?\\b","\\bjazz\\b"]}'::jsonb
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJay-qo0o1DogRX4A3IKWe2ek'
        OR lower(c.name) = lower('Comedy Plex Comedy Club'))
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.scraper_key = 'odoo_events'
   );

UPDATE scraping_sources s
   SET platform = 'custom'::"ScrapingPlatform",
       source_url = 'https://www.comedyplex.com/event',
       priority = 0,
       enabled = TRUE,
       metadata = '{"exclude_title_patterns":["\\bclass(?:es)?\\b","\\bworkshop(?:s)?\\b","\\bcamp(?:s)?\\b","\\bjazz\\b"]}'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.scraper_key = 'odoo_events'
   AND (c.google_place_id = 'ChIJay-qo0o1DogRX4A3IKWe2ek'
        OR lower(c.name) = lower('Comedy Plex Comedy Club'));
