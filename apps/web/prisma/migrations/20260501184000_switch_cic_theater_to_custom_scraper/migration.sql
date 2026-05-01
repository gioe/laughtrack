-- CIC Theater's Eventbrite organizer is stale/empty. Current show information
-- lives on the venue's Browse All Shows page as recurring weekly copy.

UPDATE scraping_sources
SET enabled = FALSE,
    updated_at = NOW()
WHERE club_id = 190
  AND platform = 'eventbrite';

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
    190,
    'custom',
    'cic_theater',
    NULL,
    'https://www.cictheater.com/browse-shows',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
WHERE NOT EXISTS (
    SELECT 1
    FROM scraping_sources
    WHERE club_id = 190
      AND platform = 'custom'
      AND priority = 0
);

UPDATE scraping_sources
SET scraper_key = 'cic_theater',
    external_id = NULL,
    source_url = 'https://www.cictheater.com/browse-shows',
    enabled = TRUE,
    metadata = '{}'::jsonb,
    updated_at = NOW()
WHERE club_id = 190
  AND platform = 'custom'
  AND priority = 0;
