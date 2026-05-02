-- Comic Strip Live's old Eventbrite venue ID returns zero live events.
-- The current source is the Eventbrite organizer page for The Comic Strip Comedy Club.

UPDATE scraping_sources
SET scraper_key = 'eventbrite',
    external_id = '8100188167',
    source_url = 'https://www.eventbrite.com/o/the-comic-strip-comedy-club-8100188167',
    enabled = TRUE,
    metadata = '{}'::jsonb,
    updated_at = NOW()
WHERE club_id = 21
  AND platform = 'eventbrite'::"ScrapingPlatform";

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
    21,
    'eventbrite',
    'eventbrite',
    '8100188167',
    'https://www.eventbrite.com/o/the-comic-strip-comedy-club-8100188167',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
WHERE NOT EXISTS (
    SELECT 1
    FROM scraping_sources
    WHERE club_id = 21
      AND platform = 'eventbrite'::"ScrapingPlatform"
);
