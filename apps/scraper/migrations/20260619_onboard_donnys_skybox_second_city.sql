-- TASK-2961: Onboard Donny's Skybox Theatre at The Second City Chicago.
--
-- The live Second City Chicago calendar exposes Donny's Skybox shows through
-- the same Second City GraphQL + entityResolver platform used by UP Comedy Club.
-- Reuse scraper_key='up_comedy_club' with a per-source venue filter so this
-- room only imports shows whose GraphQL venue metadata names Donny's Skybox.

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
    club_type,
    google_place_id
)
SELECT
    'Donny''s Skybox Theatre',
    '230 W North Ave, 4th Floor',
    'https://www.secondcity.com/locations/chicago/',
    '60610',
    '312-337-3992',
    'America/Chicago',
    TRUE,
    'Chicago',
    'IL',
    'active',
    'club',
    'ChIJQ3OUPUHTD4gRi5yVzdw_oRI'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJQ3OUPUHTD4gRi5yVzdw_oRI'
        OR lower(name) = lower('Donny''s Skybox Theatre')
);

UPDATE clubs
   SET address = '230 W North Ave, 4th Floor',
       website = 'https://www.secondcity.com/locations/chicago/',
       zip_code = '60610',
       phone_number = '312-337-3992',
       timezone = 'America/Chicago',
       visible = TRUE,
       city = 'Chicago',
       state = 'IL',
       status = 'active',
       club_type = 'club',
       google_place_id = COALESCE(google_place_id, 'ChIJQ3OUPUHTD4gRi5yVzdw_oRI')
 WHERE google_place_id = 'ChIJQ3OUPUHTD4gRi5yVzdw_oRI'
    OR lower(name) = lower('Donny''s Skybox Theatre');

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
    'up_comedy_club',
    'https://www.secondcity.com/shows/chicago/',
    0,
    TRUE,
    '{"venue_name_contains":["Donny''s Skybox Theater"]}'::jsonb
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJQ3OUPUHTD4gRi5yVzdw_oRI'
        OR lower(c.name) = lower('Donny''s Skybox Theatre'))
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.scraper_key = 'up_comedy_club'
          AND s.source_url = 'https://www.secondcity.com/shows/chicago/'
   );

UPDATE scraping_sources s
   SET platform = 'custom'::"ScrapingPlatform",
       source_url = 'https://www.secondcity.com/shows/chicago/',
       priority = 0,
       enabled = TRUE,
       metadata = '{"venue_name_contains":["Donny''s Skybox Theater"]}'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.scraper_key = 'up_comedy_club'
   AND (c.google_place_id = 'ChIJQ3OUPUHTD4gRi5yVzdw_oRI'
        OR lower(c.name) = lower('Donny''s Skybox Theatre'));
