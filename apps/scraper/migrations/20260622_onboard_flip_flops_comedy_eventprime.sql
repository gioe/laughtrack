-- TASK-3169: Onboard Flip Flops Comedy Club via the generic EventPrime scraper.
--
-- Flip Flops Comedy Club (flipflopscomedy.com; Old Orchard Beach, ME) is a
-- WordPress + WooCommerce site, but its dated shows live in the EventPrime
-- events plugin, exposed publicly + unauthenticated at
-- https://flipflopscomedy.com/wp-json/eventprime/v1/get_events . The WooCommerce
-- Store API only returns multi-show passes / EventPrime placeholders, so it is
-- NOT wired. The new generic 'eventprime' scraper (scraper_key='eventprime',
-- platform='custom') reads the get_events endpoint and maps each upcoming event
-- to a Show.
--
-- visible=TRUE: a real fixed comedy club (not a hidden proxy producer).
-- Idempotent: re-running reuses the club (matched by google_place_id, then
-- name+city+state) and the existing eventprime scraping_sources row.

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
    'Flip Flops Comedy Club',
    'Old Orchard Beach, ME 04064',
    'https://flipflopscomedy.com/',
    '04064',
    'America/New_York',
    TRUE,
    'Old Orchard Beach',
    'ME',
    'active',
    'club',
    'ChIJU3Eo5eahskwRmfT8ual7NLY'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJU3Eo5eahskwRmfT8ual7NLY'
        OR (lower(name) = lower('Flip Flops Comedy Club')
            AND lower(city) = lower('Old Orchard Beach') AND state = 'ME')
);

UPDATE clubs
   SET website = 'https://flipflopscomedy.com/',
       zip_code = '04064',
       timezone = 'America/New_York',
       visible = TRUE,
       city = 'Old Orchard Beach',
       state = 'ME',
       status = 'active',
       club_type = 'club',
       google_place_id = COALESCE(google_place_id, 'ChIJU3Eo5eahskwRmfT8ual7NLY')
 WHERE google_place_id = 'ChIJU3Eo5eahskwRmfT8ual7NLY'
    OR (lower(name) = lower('Flip Flops Comedy Club')
        AND lower(city) = lower('Old Orchard Beach') AND state = 'ME');

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
    'eventprime',
    'https://flipflopscomedy.com/wp-json/eventprime/v1/get_events',
    0,
    TRUE,
    '{}'::jsonb
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJU3Eo5eahskwRmfT8ual7NLY'
        OR (lower(c.name) = lower('Flip Flops Comedy Club')
            AND lower(c.city) = lower('Old Orchard Beach') AND c.state = 'ME'))
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.scraper_key = 'eventprime'
   );

UPDATE scraping_sources s
   SET platform = 'custom'::"ScrapingPlatform",
       source_url = 'https://flipflopscomedy.com/wp-json/eventprime/v1/get_events',
       priority = 0,
       enabled = TRUE,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.scraper_key = 'eventprime'
   AND (c.google_place_id = 'ChIJU3Eo5eahskwRmfT8ual7NLY'
        OR (lower(c.name) = lower('Flip Flops Comedy Club')
            AND lower(c.city) = lower('Old Orchard Beach') AND c.state = 'ME'));
