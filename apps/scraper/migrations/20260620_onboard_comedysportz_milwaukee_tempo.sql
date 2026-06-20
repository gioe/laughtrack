-- TASK-3022: Onboard ComedySportz Milwaukee via the new tempo_tickets scraper.
--
-- ComedySportz Milwaukee is an all-improv comedy club that sells tickets
-- exclusively through Tempo Tickets (tempotickets.com). The cszmke.com site is a
-- SpotHopper builder with no inline event data; the only ticketing link is the
-- Tempo listing (category c=80). All-comedy, so no comedy_filter. The scraper
-- builds the listing URL from the `category_id` metadata.
--
-- Idempotent: matches on google_place_id or lowercase name, and on
-- (club_id, scraper_key) for the source.

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
    'ComedySportz Milwaukee',
    '420 S 1st St',
    'https://cszmke.com/',
    '53204',
    'America/Chicago',
    TRUE,
    'Milwaukee',
    'WI',
    'active',
    'club',
    'ChIJD9azULwZBYgRouAgH_i5lrw'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJD9azULwZBYgRouAgH_i5lrw'
        OR lower(name) = lower('ComedySportz Milwaukee')
);

UPDATE clubs
   SET address = '420 S 1st St',
       website = 'https://cszmke.com/',
       zip_code = '53204',
       timezone = 'America/Chicago',
       visible = TRUE,
       city = 'Milwaukee',
       state = 'WI',
       status = 'active',
       club_type = 'club',
       google_place_id = COALESCE(google_place_id, 'ChIJD9azULwZBYgRouAgH_i5lrw')
 WHERE google_place_id = 'ChIJD9azULwZBYgRouAgH_i5lrw'
    OR lower(name) = lower('ComedySportz Milwaukee');

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
    'tempo_tickets',
    'https://www.tempotickets.com/tempotickets/site/pages/listing.php?c=80',
    0,
    TRUE,
    '{"category_id": "80"}'::jsonb
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJD9azULwZBYgRouAgH_i5lrw'
        OR lower(c.name) = lower('ComedySportz Milwaukee'))
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.scraper_key = 'tempo_tickets'
   );

UPDATE scraping_sources s
   SET platform = 'custom'::"ScrapingPlatform",
       source_url = 'https://www.tempotickets.com/tempotickets/site/pages/listing.php?c=80',
       priority = 0,
       enabled = TRUE,
       metadata = '{"category_id": "80"}'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.scraper_key = 'tempo_tickets'
   AND (c.google_place_id = 'ChIJD9azULwZBYgRouAgH_i5lrw'
        OR lower(c.name) = lower('ComedySportz Milwaukee'));
