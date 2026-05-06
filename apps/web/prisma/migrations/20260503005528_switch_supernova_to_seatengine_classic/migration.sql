-- Switch SuperNova Comedy (club 456) from the DataDome-blocked Tixr group page
-- to its fetchable SeatEngine Classic venue mirror.
--
-- Verification notes from adoption:
--   * Existing Tixr source at https://www.tixr.com/groups/supernova reproduced 0 shows.
--   * Tixr direct fetch returned DataDome 403 and Playwright fallback produced no event URLs.
--   * https://www-supernovacomedy-com.seatengine.com/ is HTTP 200 and uses classic
--     SeatEngine assets (cdn.seatengine.com/assets/application...).
--   * SeatEngine /events and /calendar are currently empty, so live-show verification
--     is blocked until the venue lists new shows.

UPDATE clubs
SET website = 'https://www-supernovacomedy-com.seatengine.com/',
    address = '1716 Whitley Ave',
    zip_code = '90028',
    timezone = 'America/Los_Angeles',
    city = 'Los Angeles',
    state = 'CA',
    country = 'US',
    visible = TRUE,
    status = 'active'
WHERE id = 456;

UPDATE scraping_sources
SET enabled = FALSE,
    updated_at = NOW()
WHERE club_id = 456
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
    456,
    'seatengine',
    'seatengine_classic',
    NULL,
    'https://www-supernovacomedy-com.seatengine.com/events',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
WHERE NOT EXISTS (
    SELECT 1
    FROM scraping_sources
    WHERE club_id = 456
      AND platform = 'seatengine'::"ScrapingPlatform"
      AND priority = 0
);

UPDATE scraping_sources
SET scraper_key = 'seatengine_classic',
    external_id = NULL,
    source_url = 'https://www-supernovacomedy-com.seatengine.com/events',
    enabled = TRUE,
    metadata = '{}'::jsonb,
    updated_at = NOW()
WHERE club_id = 456
  AND platform = 'seatengine'::"ScrapingPlatform"
  AND priority = 0;
