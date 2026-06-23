-- TASK-3167: Onboard Firehouse Theater Newport via generic FareHarbor.
--
-- Firehouse Theater is a dedicated improv/live-comedy theater in Newport, RI.
-- Its Wix site links to FareHarbor; the public FareHarbor items feed uses the
-- company shortname firehousetheater and monthly calendar JSON for show dates.

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
    'Firehouse Theater',
    '4 Equality Park Pl',
    'https://www.firehousetheater.org/',
    '02840',
    'America/New_York',
    TRUE,
    'Newport',
    'RI',
    'active',
    'club',
    'ChIJ84QwjT-v5YkRAdr4NCADXFE'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJ84QwjT-v5YkRAdr4NCADXFE'
        OR lower(name) = lower('Firehouse Theater')
);

UPDATE clubs
   SET address = '4 Equality Park Pl',
       website = 'https://www.firehousetheater.org/',
       zip_code = '02840',
       timezone = 'America/New_York',
       visible = TRUE,
       city = 'Newport',
       state = 'RI',
       status = 'active',
       club_type = 'club',
       google_place_id = COALESCE(google_place_id, 'ChIJ84QwjT-v5YkRAdr4NCADXFE')
 WHERE google_place_id = 'ChIJ84QwjT-v5YkRAdr4NCADXFE'
    OR lower(name) = lower('Firehouse Theater');

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
    'fareharbor',
    'https://fareharbor.com/embeds/book/firehousetheater/',
    0,
    TRUE,
    jsonb_build_object(
        'shortname', 'firehousetheater',
        'exclude_item_pks', jsonb_build_array(187485, 232371, 695268),
        'months_ahead', 12
    )
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJ84QwjT-v5YkRAdr4NCADXFE'
        OR lower(c.name) = lower('Firehouse Theater'))
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.platform = 'custom'::"ScrapingPlatform"
          AND s.priority = 0
   );

UPDATE scraping_sources s
   SET scraper_key = 'fareharbor',
       source_url = 'https://fareharbor.com/embeds/book/firehousetheater/',
       enabled = TRUE,
       metadata = jsonb_build_object(
           'shortname', 'firehousetheater',
           'exclude_item_pks', jsonb_build_array(187485, 232371, 695268),
           'months_ahead', 12
       ),
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.platform = 'custom'::"ScrapingPlatform"
   AND s.priority = 0
   AND (c.google_place_id = 'ChIJ84QwjT-v5YkRAdr4NCADXFE'
        OR lower(c.name) = lower('Firehouse Theater'));
