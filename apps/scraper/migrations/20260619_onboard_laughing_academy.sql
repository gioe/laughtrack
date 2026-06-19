-- TASK-2968: Onboard The Laughing Academy venue shell.
--
-- The venue is active and hosts stand-up/improv comedy, but its public show
-- page only offers a mailing-list CTA and the linked Sawyer schedule exposes
-- class/camp tabs without public show/activity inventory. Keep the club hidden
-- and do not create a scraping_sources row until a real show calendar exists.

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
    '60026',
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
       zip_code = '60026',
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
