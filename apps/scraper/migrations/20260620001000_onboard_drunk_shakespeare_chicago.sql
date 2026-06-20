-- TASK-2990: Onboard Drunk Shakespeare Chicago.
--
-- The official Drunk Shakespeare city selector links Chicago tickets to
-- BrassTix. The BrassTix calendar embeds purchasable performances in inline
-- eventArray JavaScript, parsed by scraper_key='brasstix'.

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
    'Drunk Shakespeare Chicago',
    '182 N Wabash Ave',
    'https://drunkshakespeare.com/',
    '60601',
    'America/Chicago',
    TRUE,
    'Chicago',
    'IL',
    'active',
    'club',
    'ChIJrfZzVIQtDogRTFGBr3Xglng'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJrfZzVIQtDogRTFGBr3Xglng'
        OR lower(name) = lower('Drunk Shakespeare Chicago')
);

UPDATE clubs
   SET address = '182 N Wabash Ave',
       website = 'https://drunkshakespeare.com/',
       zip_code = '60601',
       timezone = 'America/Chicago',
       visible = TRUE,
       city = 'Chicago',
       state = 'IL',
       status = 'active',
       club_type = 'club',
       google_place_id = COALESCE(google_place_id, 'ChIJrfZzVIQtDogRTFGBr3Xglng')
 WHERE google_place_id = 'ChIJrfZzVIQtDogRTFGBr3Xglng'
    OR lower(name) = lower('Drunk Shakespeare Chicago');

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
    'brasstix',
    'https://brasstix.com/pmt/calendar.php?Show=DrunkChicago',
    0,
    TRUE,
    '{}'::jsonb
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJrfZzVIQtDogRTFGBr3Xglng'
        OR lower(c.name) = lower('Drunk Shakespeare Chicago'))
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.scraper_key = 'brasstix'
   );

UPDATE scraping_sources s
   SET platform = 'custom'::"ScrapingPlatform",
       source_url = 'https://brasstix.com/pmt/calendar.php?Show=DrunkChicago',
       priority = 0,
       enabled = TRUE,
       metadata = '{}'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.scraper_key = 'brasstix'
   AND (c.google_place_id = 'ChIJrfZzVIQtDogRTFGBr3Xglng'
        OR lower(c.name) = lower('Drunk Shakespeare Chicago'));
