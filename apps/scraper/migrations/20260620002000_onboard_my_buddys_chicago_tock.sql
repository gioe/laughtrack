-- TASK-2993: Onboard My Buddy's in Chicago.
--
-- My Buddy's is a Duda venue site whose events page links to Tock ticket
-- pages. The Tock business page renders calendar events into Redux state,
-- parsed by scraper_key='tock'. The calendar is mixed-use, so enable the
-- comedy keyword filter for this source.

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
    'My Buddy''s',
    '4416 N Clark St',
    'https://www.mybuddyschicago.com/',
    '60640',
    'America/Chicago',
    TRUE,
    'Chicago',
    'IL',
    'active',
    'club',
    'ChIJhxdd7jDSD4gRtWIfVg-2ApE'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJhxdd7jDSD4gRtWIfVg-2ApE'
        OR lower(name) = lower('My Buddy''s')
);

UPDATE clubs
   SET address = '4416 N Clark St',
       website = 'https://www.mybuddyschicago.com/',
       zip_code = '60640',
       timezone = 'America/Chicago',
       visible = TRUE,
       city = 'Chicago',
       state = 'IL',
       status = 'active',
       club_type = 'club',
       google_place_id = COALESCE(google_place_id, 'ChIJhxdd7jDSD4gRtWIfVg-2ApE')
 WHERE google_place_id = 'ChIJhxdd7jDSD4gRtWIfVg-2ApE'
    OR lower(name) = lower('My Buddy''s');

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
    'tock',
    'https://www.exploretock.com/mybuddys',
    0,
    TRUE,
    '{"comedy_filter": true}'::jsonb
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJhxdd7jDSD4gRtWIfVg-2ApE'
        OR lower(c.name) = lower('My Buddy''s'))
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.scraper_key = 'tock'
   );

UPDATE scraping_sources s
   SET platform = 'custom'::"ScrapingPlatform",
       source_url = 'https://www.exploretock.com/mybuddys',
       priority = 0,
       enabled = TRUE,
       metadata = '{"comedy_filter": true}'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.scraper_key = 'tock'
   AND (c.google_place_id = 'ChIJhxdd7jDSD4gRtWIfVg-2ApE'
        OR lower(c.name) = lower('My Buddy''s'));
