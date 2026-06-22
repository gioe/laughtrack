-- TASK-3164: Onboard Rascals Worcester via Modern Events Calendar.
--
-- Rascals uses WordPress Modern Events Calendar with comedy category id 28:
-- https://rascalsworcester.com/wp-json/wp/v2/mec-events?mec_category=28
-- Detail pages do not emit schema.org Event JSON-LD, so the generic MEC scraper
-- uses its HTML fallback for .mec-single-event-date / time / cost fields.

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
    'Rascals Worcester',
    '70 James St',
    'https://rascalsworcester.com',
    '01603',
    'America/New_York',
    TRUE,
    'Worcester',
    'MA',
    'active',
    'venue',
    'ChIJUTQ0V4UF5IkRJX7r_nMfZI0'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJUTQ0V4UF5IkRJX7r_nMfZI0'
        OR (lower(name) IN (lower('Rascals Worcester'), lower('Rascals'))
            AND lower(city) = lower('Worcester')
            AND state = 'MA')
);

UPDATE clubs
   SET address = '70 James St',
       website = 'https://rascalsworcester.com',
       zip_code = '01603',
       timezone = 'America/New_York',
       visible = TRUE,
       city = 'Worcester',
       state = 'MA',
       status = 'active',
       club_type = 'venue',
       google_place_id = COALESCE(google_place_id, 'ChIJUTQ0V4UF5IkRJX7r_nMfZI0')
 WHERE google_place_id = 'ChIJUTQ0V4UF5IkRJX7r_nMfZI0'
    OR (lower(name) IN (lower('Rascals Worcester'), lower('Rascals'))
        AND lower(city) = lower('Worcester')
        AND state = 'MA');

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
    'modern_events_calendar',
    'https://rascalsworcester.com/wp-json/wp/v2/mec-events?mec_category=28',
    0,
    TRUE,
    '{
        "listing_url": "https://rascalsworcester.com/event-category/comedy/",
        "force_js_rendering": true,
        "per_page": 20,
        "max_pages": 2,
        "max_detail_pages": 40,
        "mec_category": 28
    }'::jsonb
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJUTQ0V4UF5IkRJX7r_nMfZI0'
        OR (lower(c.name) IN (lower('Rascals Worcester'), lower('Rascals'))
            AND lower(c.city) = lower('Worcester')
            AND c.state = 'MA'))
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.scraper_key = 'modern_events_calendar'
          AND s.source_url = 'https://rascalsworcester.com/wp-json/wp/v2/mec-events?mec_category=28'
   );

UPDATE scraping_sources s
   SET platform = 'custom'::"ScrapingPlatform",
       source_url = 'https://rascalsworcester.com/wp-json/wp/v2/mec-events?mec_category=28',
       priority = 0,
       enabled = TRUE,
       metadata = '{
           "listing_url": "https://rascalsworcester.com/event-category/comedy/",
           "force_js_rendering": true,
           "per_page": 20,
           "max_pages": 2,
           "max_detail_pages": 40,
           "mec_category": 28
       }'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.scraper_key = 'modern_events_calendar'
   AND (c.google_place_id = 'ChIJUTQ0V4UF5IkRJX7r_nMfZI0'
        OR (lower(c.name) IN (lower('Rascals Worcester'), lower('Rascals'))
            AND lower(c.city) = lower('Worcester')
            AND c.state = 'MA'));
