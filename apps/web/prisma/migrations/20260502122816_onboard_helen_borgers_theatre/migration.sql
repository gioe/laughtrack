-- Onboard Helen Borgers Theatre (Long Beach, CA) using its SeatEngine Classic events page.

UPDATE clubs
SET address = '4250 Atlantic Ave.',
    website = 'https://www.lbshakespeare.org',
    zip_code = '90807',
    timezone = 'America/Los_Angeles',
    city = 'Long Beach',
    state = 'CA',
    country = 'US',
    visible = TRUE,
    status = 'active'
WHERE id = 424;

UPDATE scraping_sources
SET enabled = FALSE,
    updated_at = NOW()
WHERE club_id = 424
  AND NOT (platform = 'seatengine'::"ScrapingPlatform" AND priority = 0);

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
    424,
    'seatengine',
    'seatengine_classic',
    NULL,
    'https://www-lbshakespeare-org.seatengine.com/events',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
WHERE NOT EXISTS (
    SELECT 1
    FROM scraping_sources
    WHERE club_id = 424
      AND platform = 'seatengine'::"ScrapingPlatform"
      AND priority = 0
);

UPDATE scraping_sources
SET scraper_key = 'seatengine_classic',
    external_id = NULL,
    source_url = 'https://www-lbshakespeare-org.seatengine.com/events',
    enabled = TRUE,
    metadata = '{}'::jsonb,
    updated_at = NOW()
WHERE club_id = 424
  AND platform = 'seatengine'::"ScrapingPlatform"
  AND priority = 0;
