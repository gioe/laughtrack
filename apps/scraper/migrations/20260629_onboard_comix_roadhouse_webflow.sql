-- Onboard Comix Roadhouse at Mohegan Sun via a venue-specific Webflow scraper.
--
-- The public calendar is server-rendered Webflow HTML. The comedy-club listing
-- links to /comics/<slug> detail pages, and each detail page contains the
-- authoritative per-performance date/time plus Leap Events ticket URL.
--
-- Idempotent (re-runs nightly via bin/migrate): INSERT ... WHERE NOT EXISTS +
-- guarded UPDATE, matched on lower(name).

INSERT INTO clubs (
    name,
    address,
    website,
    zip_code,
    phone_number,
    timezone,
    visible,
    city,
    state,
    status,
    club_type
)
SELECT
    'Comix Roadhouse',
    '1 Mohegan Sun Blvd',
    'https://www.comixroadhouse.com/',
    '06382',
    '860-862-7000',
    'America/New_York',
    TRUE,
    'Uncasville',
    'CT',
    'active',
    'club'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE lower(name) = lower('Comix Roadhouse')
);

UPDATE clubs
   SET address = '1 Mohegan Sun Blvd',
       website = 'https://www.comixroadhouse.com/',
       zip_code = '06382',
       phone_number = '860-862-7000',
       timezone = 'America/New_York',
       visible = TRUE,
       city = 'Uncasville',
       state = 'CT',
       status = 'active',
       club_type = 'club'
 WHERE lower(name) = lower('Comix Roadhouse');

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
    'comix_roadhouse',
    'https://www.comixroadhouse.com/calendar/in-the-comedy-club',
    0,
    TRUE,
    '{}'::jsonb
  FROM clubs c
 WHERE lower(c.name) = lower('Comix Roadhouse')
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.platform = 'custom'::"ScrapingPlatform"
          AND s.priority = 0
   );

UPDATE scraping_sources s
   SET scraper_key = 'comix_roadhouse',
       source_url = 'https://www.comixroadhouse.com/calendar/in-the-comedy-club',
       enabled = TRUE,
       metadata = '{}'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.platform = 'custom'::"ScrapingPlatform"
   AND s.priority = 0
   AND lower(c.name) = lower('Comix Roadhouse');
