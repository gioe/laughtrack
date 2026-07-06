-- Onboard Greenwich Village Comedy Club via its WordPress shows API and Tessera tickets.

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
    'Greenwich Village Comedy Club',
    '99 MacDougal St',
    'https://www.greenwichvillagecomedyclub.com',
    0,
    '10012',
    '646-470-7582',
    true,
    'America/New_York',
    'New York',
    'NY',
    'US',
    'active',
    'club'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE lower(name) = lower('Greenwich Village Comedy Club')
);

UPDATE clubs
   SET address = '99 MacDougal St',
       website = 'https://www.greenwichvillagecomedyclub.com',
       zip_code = '10012',
       phone_number = '646-470-7582',
       visible = true,
       timezone = 'America/New_York',
       city = 'New York',
       state = 'NY',
       country = 'US',
       status = 'active',
       club_type = 'club'
 WHERE lower(name) = lower('Greenwich Village Comedy Club');

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
    'greenwich_village_comedy_club',
    'https://www.greenwichvillagecomedyclub.com/wp-json/wp/v2/shows?per_page=100&page=1',
    0,
    true,
    '{}'::jsonb
  FROM clubs c
 WHERE lower(c.name) = lower('Greenwich Village Comedy Club')
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.platform = 'custom'::"ScrapingPlatform"
          AND s.priority = 0
   );

UPDATE scraping_sources s
   SET scraper_key = 'greenwich_village_comedy_club',
       source_url = 'https://www.greenwichvillagecomedyclub.com/wp-json/wp/v2/shows?per_page=100&page=1',
       enabled = true,
       metadata = '{}'::jsonb,
       updated_at = now()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.platform = 'custom'::"ScrapingPlatform"
   AND s.priority = 0
   AND lower(c.name) = lower('Greenwich Village Comedy Club');
