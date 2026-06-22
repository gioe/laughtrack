-- TASK-3168: Onboard The Colonial Theatre via generic OvationTix.
--
-- The Colonial is a mixed-use performing-arts center. OvationTix client 36697
-- includes concerts, film screenings, theater, and stand-up comedy, so this
-- source opts into the shared comedy filter. The allowlist preserves name-only
-- touring-comedian titles that may not carry comedy keywords in the feed.

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
    'The Colonial Theatre',
    '95 Main Street',
    'https://www.thecolonial.org',
    '03431',
    'America/New_York',
    TRUE,
    'Keene',
    'NH',
    'active',
    'venue',
    'ChIJ453HtoBz4YkRCrrHlZU2Eq8'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJ453HtoBz4YkRCrrHlZU2Eq8'
        OR (lower(name) = lower('The Colonial Theatre') AND lower(city) = lower('Keene') AND state = 'NH')
);

UPDATE clubs
   SET address = '95 Main Street',
       website = 'https://www.thecolonial.org',
       zip_code = '03431',
       timezone = 'America/New_York',
       visible = TRUE,
       city = 'Keene',
       state = 'NH',
       status = 'active',
       club_type = 'venue',
       google_place_id = COALESCE(google_place_id, 'ChIJ453HtoBz4YkRCrrHlZU2Eq8')
 WHERE google_place_id = 'ChIJ453HtoBz4YkRCrrHlZU2Eq8'
    OR (lower(name) = lower('The Colonial Theatre') AND lower(city) = lower('Keene') AND state = 'NH');

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    ovationtix_id,
    priority,
    enabled,
    metadata
)
SELECT
    c.id,
    'ovationtix'::"ScrapingPlatform",
    'ovationtix',
    'https://web.ovationtix.com/trs/cal/36697',
    '36697',
    0,
    TRUE,
    '{
        "comedy_filter": true,
        "comedy_title_allowlist": [
            "Patton Oswalt",
            "Margaret Cho",
            "Juston McKinney",
            "Frank Santos",
            "Nurse Blake"
        ],
        "exclude_title_patterns": [
            "^FILM:",
            "Philharmonic",
            "Ballet",
            "Dance Company"
        ]
    }'::jsonb
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJ453HtoBz4YkRCrrHlZU2Eq8'
        OR (lower(c.name) = lower('The Colonial Theatre') AND lower(c.city) = lower('Keene') AND c.state = 'NH'))
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.scraper_key = 'ovationtix'
          AND s.ovationtix_id = '36697'
   );

UPDATE scraping_sources s
   SET platform = 'ovationtix'::"ScrapingPlatform",
       source_url = 'https://web.ovationtix.com/trs/cal/36697',
       ovationtix_id = '36697',
       priority = 0,
       enabled = TRUE,
       metadata = '{
           "comedy_filter": true,
           "comedy_title_allowlist": [
               "Patton Oswalt",
               "Margaret Cho",
               "Juston McKinney",
               "Frank Santos",
               "Nurse Blake"
           ],
           "exclude_title_patterns": [
               "^FILM:",
               "Philharmonic",
               "Ballet",
               "Dance Company"
           ]
       }'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.scraper_key = 'ovationtix'
   AND (c.google_place_id = 'ChIJ453HtoBz4YkRCrrHlZU2Eq8'
        OR (lower(c.name) = lower('The Colonial Theatre') AND lower(c.city) = lower('Keene') AND c.state = 'NH'));
