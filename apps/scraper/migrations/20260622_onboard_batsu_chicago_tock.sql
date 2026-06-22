-- TASK-3014: Onboard BATSU! Chicago via generic Tock.
--
-- BATSU! Chicago is a live Japanese-American comedy show. The public venue
-- page points to exploretock.com/batsu-chicago; the Tock business page renders
-- recurring PRIX_FIXE reservation dates/times into window.$REDUX_STATE.

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
    'BATSU! Chicago',
    '1531 N Wells St',
    'https://batsulive.com/chicago/',
    '60610',
    'America/Chicago',
    TRUE,
    'Chicago',
    'IL',
    'active',
    'club',
    'ChIJn0ISwOTTD4gRqnNcfcXrM3Q'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJn0ISwOTTD4gRqnNcfcXrM3Q'
        OR lower(name) = lower('BATSU! Chicago')
);

UPDATE clubs
   SET address = '1531 N Wells St',
       website = 'https://batsulive.com/chicago/',
       zip_code = '60610',
       timezone = 'America/Chicago',
       visible = TRUE,
       city = 'Chicago',
       state = 'IL',
       status = 'active',
       club_type = 'club',
       google_place_id = COALESCE(google_place_id, 'ChIJn0ISwOTTD4gRqnNcfcXrM3Q')
 WHERE google_place_id = 'ChIJn0ISwOTTD4gRqnNcfcXrM3Q'
    OR lower(name) = lower('BATSU! Chicago');

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
    'tock',
    'https://www.exploretock.com/batsu-chicago',
    0,
    TRUE,
    '{}'::jsonb
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJn0ISwOTTD4gRqnNcfcXrM3Q'
        OR lower(c.name) = lower('BATSU! Chicago'))
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.platform = 'custom'::"ScrapingPlatform"
          AND s.priority = 0
   );

UPDATE scraping_sources s
   SET scraper_key = 'tock',
       source_url = 'https://www.exploretock.com/batsu-chicago',
       enabled = TRUE,
       metadata = '{}'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.platform = 'custom'::"ScrapingPlatform"
   AND s.priority = 0
   AND (c.google_place_id = 'ChIJn0ISwOTTD4gRqnNcfcXrM3Q'
        OR lower(c.name) = lower('BATSU! Chicago'));
