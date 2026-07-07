-- Onboard Quezada's Comedy Club & Cantina (Santa Ana Star Casino, Santa Ana
-- Pueblo NM) via the new HoldMyTicket whitelabel scraper (TASK-3610).
-- quezadascomedyclub.com is a parked lander; the branded whitelabel site
-- quezadas.holdmyticket.com is the club's real events presence.

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
    'Quezada''s Comedy Club & Cantina',
    '54 Jemez Canyon Dam Rd',
    'https://quezadas.holdmyticket.com',
    0,
    '87004',
    '',
    true,
    'America/Denver',
    'Santa Ana Pueblo',
    'NM',
    'US',
    'active',
    'club'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE lower(name) = lower('Quezada''s Comedy Club & Cantina')
);

UPDATE clubs
   SET address = '54 Jemez Canyon Dam Rd',
       website = 'https://quezadas.holdmyticket.com',
       zip_code = '87004',
       visible = true,
       timezone = 'America/Denver',
       city = 'Santa Ana Pueblo',
       state = 'NM',
       country = 'US',
       status = 'active',
       club_type = 'club'
 WHERE lower(name) = lower('Quezada''s Comedy Club & Cantina');

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
    'holdmyticket',
    'https://quezadas.holdmyticket.com/',
    0,
    true,
    '{}'::jsonb
  FROM clubs c
 WHERE lower(c.name) = lower('Quezada''s Comedy Club & Cantina')
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.platform = 'custom'::"ScrapingPlatform"
          AND s.priority = 0
   );

UPDATE scraping_sources s
   SET scraper_key = 'holdmyticket',
       source_url = 'https://quezadas.holdmyticket.com/',
       enabled = true,
       metadata = '{}'::jsonb,
       updated_at = now()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.platform = 'custom'::"ScrapingPlatform"
   AND s.priority = 0
   AND lower(c.name) = lower('Quezada''s Comedy Club & Cantina');
