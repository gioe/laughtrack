-- Go Bananas Comedy Club's SeatEngine venue endpoint is valid but currently
-- returns zero shows. The public website root contains the ticketed showtimes
-- in custom WordPress markup, so switch the active source to the custom scraper.

UPDATE scraping_sources
SET enabled = FALSE,
    updated_at = NOW()
WHERE club_id = 574
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
    574,
    'custom',
    'go_bananas',
    NULL,
    'https://gobananascomedy.com',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
WHERE NOT EXISTS (
    SELECT 1
    FROM scraping_sources
    WHERE club_id = 574
      AND platform = 'custom'
      AND priority = 0
);

UPDATE scraping_sources
SET scraper_key = 'go_bananas',
    external_id = NULL,
    source_url = 'https://gobananascomedy.com',
    enabled = TRUE,
    metadata = '{}'::jsonb,
    updated_at = NOW()
WHERE club_id = 574
  AND platform = 'custom'
  AND priority = 0;

UPDATE clubs
SET website = 'https://gobananascomedy.com',
    timezone = COALESCE(timezone, 'America/New_York')
WHERE id = 574;
