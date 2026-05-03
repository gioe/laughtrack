-- Palm Beach Improv's legacy domain redirects to the Kravis Center Improv page.
-- SeatEngine venue 350 is still valid metadata but currently returns zero shows.

UPDATE scraping_sources
SET enabled = FALSE,
    updated_at = NOW()
WHERE club_id = 379
  AND platform = 'seatengine';

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    external_id,
    source_url,
    enabled,
    priority,
    metadata,
    created_at,
    updated_at
)
SELECT
    379,
    'custom',
    'palm_beach_improv',
    NULL,
    'https://www.kravis.org/performance-calendar/improv/',
    TRUE,
    0,
    '{"previous_seatengine_id":"350"}'::jsonb,
    NOW(),
    NOW()
WHERE NOT EXISTS (
    SELECT 1
    FROM scraping_sources
    WHERE club_id = 379
      AND platform = 'custom'
      AND priority = 0
);

UPDATE scraping_sources
SET scraper_key = 'palm_beach_improv',
    external_id = NULL,
    source_url = 'https://www.kravis.org/performance-calendar/improv/',
    enabled = TRUE,
    metadata = '{"previous_seatengine_id":"350"}'::jsonb,
    updated_at = NOW()
WHERE club_id = 379
  AND platform = 'custom'
  AND priority = 0;

UPDATE clubs
SET website = 'https://www.kravis.org/performance-calendar/improv/',
    address = '701 Okeechobee Boulevard',
    city = 'West Palm Beach',
    state = 'FL',
    zip_code = '33401',
    timezone = 'America/New_York',
    phone_number = COALESCE(NULLIF(phone_number, ''), '561.832.7469')
WHERE id = 379;
