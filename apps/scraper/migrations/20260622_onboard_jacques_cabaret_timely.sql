-- TASK-3155: Onboard Jacques' Cabaret via the generic Timely scraper.
--
-- Jacques' Cabaret embeds a Timely / time.ly calendar at
-- https://events.timely.fun/fwq8raf8/agenda. The page's browser API calls use
-- calendar id 54755528 and Timely's public x-api-key header.

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
    'Jacques'' Cabaret',
    '79 Broadway',
    'https://www.jacquescabaret.com/v3/',
    '02116',
    'America/New_York',
    TRUE,
    'Boston',
    'MA',
    'active',
    'club',
    'ChIJs5_lpnZ644kRsXIr0d6sgQY'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJs5_lpnZ644kRsXIr0d6sgQY'
        OR (lower(name) = lower('Jacques'' Cabaret') AND lower(city) = lower('Boston') AND state = 'MA')
);

UPDATE clubs
   SET address = '79 Broadway',
       website = 'https://www.jacquescabaret.com/v3/',
       zip_code = '02116',
       timezone = 'America/New_York',
       visible = TRUE,
       city = 'Boston',
       state = 'MA',
       status = 'active',
       club_type = 'club',
       google_place_id = COALESCE(google_place_id, 'ChIJs5_lpnZ644kRsXIr0d6sgQY')
 WHERE google_place_id = 'ChIJs5_lpnZ644kRsXIr0d6sgQY'
    OR (lower(name) = lower('Jacques'' Cabaret') AND lower(city) = lower('Boston') AND state = 'MA');

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
    'timely',
    'https://events.timely.fun/fwq8raf8/agenda',
    0,
    TRUE,
    '{"timely_calendar_id": 54755528, "calendar_slug": "fwq8raf8"}'::jsonb
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJs5_lpnZ644kRsXIr0d6sgQY'
        OR (lower(c.name) = lower('Jacques'' Cabaret') AND lower(c.city) = lower('Boston') AND c.state = 'MA'))
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.scraper_key = 'timely'
   );

UPDATE scraping_sources s
   SET platform = 'custom'::"ScrapingPlatform",
       source_url = 'https://events.timely.fun/fwq8raf8/agenda',
       priority = 0,
       enabled = TRUE,
       metadata = '{"timely_calendar_id": 54755528, "calendar_slug": "fwq8raf8"}'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.scraper_key = 'timely'
   AND (c.google_place_id = 'ChIJs5_lpnZ644kRsXIr0d6sgQY'
        OR (lower(c.name) = lower('Jacques'' Cabaret') AND lower(c.city) = lower('Boston') AND c.state = 'MA'));

