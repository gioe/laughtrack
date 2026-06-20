-- TASK-2962: Add The Home Comedy Theater as a pre-launch venue shell.
--
-- The venue is real and has a legitimate address, but it has not published
-- public shows yet. The clubs.status constraint only permits active, closed,
-- and hiatus, so use hiatus for the club row and keep the more precise
-- not_open_yet marker in the disabled none scraper source metadata.

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
    'The Home Comedy Theater',
    '2843 N Halsted St',
    'https://homecomedytheater.com/',
    '60657',
    'America/Chicago',
    FALSE,
    'Chicago',
    'IL',
    'hiatus',
    'club',
    'ChIJszI0pGvTD4gRQJJ5CYItf-k'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJszI0pGvTD4gRQJJ5CYItf-k'
        OR lower(name) = lower('The Home Comedy Theater')
);

UPDATE clubs
   SET address = '2843 N Halsted St',
       website = 'https://homecomedytheater.com/',
       zip_code = '60657',
       timezone = 'America/Chicago',
       visible = FALSE,
       city = 'Chicago',
       state = 'IL',
       status = 'hiatus',
       club_type = 'club',
       google_place_id = COALESCE(google_place_id, 'ChIJszI0pGvTD4gRQJJ5CYItf-k')
 WHERE google_place_id = 'ChIJszI0pGvTD4gRQJJ5CYItf-k'
    OR lower(name) = lower('The Home Comedy Theater');

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
    'none',
    'https://homecomedytheater.com/',
    0,
    FALSE,
    '{
        "status": "not_open_yet",
        "reason": "Venue is pre-launch; no published public shows yet.",
        "future_scraper_key": "the_events_calendar",
        "future_source_url": "https://homecomedytheater.com/wp-json/tribe/events/v1/events"
    }'::jsonb
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJszI0pGvTD4gRQJJ5CYItf-k'
        OR lower(c.name) = lower('The Home Comedy Theater'))
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.scraper_key = 'none'
   );

UPDATE scraping_sources s
   SET platform = 'custom'::"ScrapingPlatform",
       source_url = 'https://homecomedytheater.com/',
       priority = 0,
       enabled = FALSE,
       metadata = '{
           "status": "not_open_yet",
           "reason": "Venue is pre-launch; no published public shows yet.",
           "future_scraper_key": "the_events_calendar",
           "future_source_url": "https://homecomedytheater.com/wp-json/tribe/events/v1/events"
       }'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.scraper_key = 'none'
   AND (c.google_place_id = 'ChIJszI0pGvTD4gRQJJ5CYItf-k'
        OR lower(c.name) = lower('The Home Comedy Theater'));
