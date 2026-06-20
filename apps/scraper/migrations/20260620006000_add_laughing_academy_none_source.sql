-- TASK-3019: Add The Laughing Academy as a venue shell with no scraper.
--
-- The venue is real and operates at a single Glenview address, but its public
-- show page currently exposes a mailing-list CTA rather than dated show
-- inventory. Keep the club hidden and add a disabled none source so the venue
-- is tracked without scraper runs importing classes or camps.

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
    latitude,
    longitude,
    google_place_id
)
SELECT
    'The Laughing Academy',
    '3230 Glenview Rd',
    'https://thelaughingacademy.com/',
    '60025',
    '847-724-2787',
    'America/Chicago',
    FALSE,
    'Glenview',
    'IL',
    'active',
    'club',
    42.0732665,
    -87.8386645,
    'ChIJ__-TFL_HD4gRhm7llCdnPBI'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJ__-TFL_HD4gRhm7llCdnPBI'
        OR lower(name) = lower('The Laughing Academy')
);

UPDATE clubs
   SET address = '3230 Glenview Rd',
       website = 'https://thelaughingacademy.com/',
       zip_code = '60025',
       phone_number = '847-724-2787',
       timezone = 'America/Chicago',
       visible = FALSE,
       city = 'Glenview',
       state = 'IL',
       status = 'active',
       club_type = 'club',
       latitude = COALESCE(latitude, 42.0732665),
       longitude = COALESCE(longitude, -87.8386645),
       google_place_id = COALESCE(google_place_id, 'ChIJ__-TFL_HD4gRhm7llCdnPBI')
 WHERE google_place_id = 'ChIJ__-TFL_HD4gRhm7llCdnPBI'
    OR lower(name) = lower('The Laughing Academy');

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
    'none',
    'https://thelaughingacademy.com/on-stage-now',
    0,
    FALSE,
    '{
        "status": "no_show_inventory",
        "reason": "On Stage Now page currently has a mailing-list CTA but no dated public show inventory.",
        "checked_at": "2026-06-20",
        "class_registration_url": "https://www.hisawyer.com/the-laughing-academy/schedules"
    }'::jsonb
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJ__-TFL_HD4gRhm7llCdnPBI'
        OR lower(c.name) = lower('The Laughing Academy'))
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.scraper_key = 'none'
   );

UPDATE scraping_sources s
   SET platform = 'custom'::"ScrapingPlatform",
       source_url = 'https://thelaughingacademy.com/on-stage-now',
       priority = 0,
       enabled = FALSE,
       metadata = '{
           "status": "no_show_inventory",
           "reason": "On Stage Now page currently has a mailing-list CTA but no dated public show inventory.",
           "checked_at": "2026-06-20",
           "class_registration_url": "https://www.hisawyer.com/the-laughing-academy/schedules"
       }'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.scraper_key = 'none'
   AND (c.google_place_id = 'ChIJ__-TFL_HD4gRhm7llCdnPBI'
        OR lower(c.name) = lower('The Laughing Academy'));
