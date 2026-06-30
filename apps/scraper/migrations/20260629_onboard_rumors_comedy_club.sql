-- Onboard Rumor's Comedy Club (Winnipeg) via venue-specific Nuxt payload scraper.

INSERT INTO clubs (
    name,
    address,
    website,
    popularity,
    zip_code,
    phone_number,
    visible,
    timezone,
    city,
    state,
    country,
    status,
    club_type
)
SELECT
    'Rumor''s Comedy Club',
    '190-2025 Corydon Avenue',
    'https://rumorscomedyclub.com/',
    0,
    'R3P 0N5',
    '(204) 488-4520',
    true,
    'America/Winnipeg',
    'Winnipeg',
    'MB',
    'CA',
    'active',
    'club'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE lower(name) = lower('Rumor''s Comedy Club')
);

UPDATE clubs
   SET address = '190-2025 Corydon Avenue',
       website = 'https://rumorscomedyclub.com/',
       zip_code = 'R3P 0N5',
       phone_number = '(204) 488-4520',
       visible = true,
       timezone = 'America/Winnipeg',
       city = 'Winnipeg',
       state = 'MB',
       country = 'CA',
       status = 'active',
       club_type = 'club'
 WHERE lower(name) = lower('Rumor''s Comedy Club');

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
    'rumors_comedy_club',
    'https://rumorscomedyclub.com/events',
    0,
    true,
    '{}'::jsonb
  FROM clubs c
 WHERE lower(c.name) = lower('Rumor''s Comedy Club')
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.platform = 'custom'::"ScrapingPlatform"
          AND s.priority = 0
   );

UPDATE scraping_sources s
   SET scraper_key = 'rumors_comedy_club',
       source_url = 'https://rumorscomedyclub.com/events',
       enabled = true,
       metadata = '{}'::jsonb,
       updated_at = now()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.platform = 'custom'::"ScrapingPlatform"
   AND s.priority = 0
   AND lower(c.name) = lower('Rumor''s Comedy Club');
