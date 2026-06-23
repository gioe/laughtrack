-- Onboard Endgames Improv (San Francisco, CA) via the generic Eventbrite scraper - TASK-3180.
--
-- Verification notes (2026-06-23):
-- * Venue site https://endgamesimprov.com/shows/ lists live improv comedy shows and links
--   each show to Eventbrite ticket pages.
-- * Eventbrite organizer: Endgames Improv, https://www.eventbrite.com/o/endgames-improv-1465732808.
-- * The discovered Google venue at 2965 Mission St maps to Eventbrite venue id 71439459
--   ("Endgames Improv Theater"). Venue-mode scraping returned 14 future shows.
--
-- The prior verification organizer scrape may have already upserted several
-- Eventbrite venue-name variants at runtime, so this migration selects one
-- canonical 2965 Mission club row and normalizes only that row/source.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Endgames Improv Theater',
    '2965 Mission St, San Francisco, CA 94110, USA',
    'https://endgamesimprov.com/',
    'San Francisco',
    'CA',
    '94110',
    'America/Los_Angeles',
    'US',
    'club',
    'ChIJ_xeIOiJ-j4ARBaKTfr3eEIo',
    TRUE,
    'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJ_xeIOiJ-j4ARBaKTfr3eEIo'
       OR lower(name) = lower('Endgames Improv Theater')
       OR (
           lower(name) = lower('Endgames Improv')
           AND address ILIKE '2965 Mission%'
       )
);

WITH target_club AS (
    SELECT id
    FROM clubs
    WHERE google_place_id = 'ChIJ_xeIOiJ-j4ARBaKTfr3eEIo'
       OR lower(name) = lower('Endgames Improv Theater')
       OR (
           lower(name) = lower('Endgames Improv')
           AND address ILIKE '2965 Mission%'
       )
    ORDER BY
        CASE
            WHEN google_place_id = 'ChIJ_xeIOiJ-j4ARBaKTfr3eEIo' THEN 0
            WHEN lower(name) = lower('Endgames Improv Theater') THEN 1
            ELSE 2
        END,
        id
    LIMIT 1
)
UPDATE clubs c
SET
    name = 'Endgames Improv Theater',
    address = '2965 Mission St, San Francisco, CA 94110, USA',
    website = 'https://endgamesimprov.com/',
    city = 'San Francisco',
    state = 'CA',
    zip_code = '94110',
    timezone = 'America/Los_Angeles',
    country = 'US',
    club_type = 'club',
    google_place_id = 'ChIJ_xeIOiJ-j4ARBaKTfr3eEIo',
    visible = TRUE,
    status = 'active'
FROM target_club t
WHERE c.id = t.id;

WITH target_club AS (
    SELECT id
    FROM clubs
    WHERE google_place_id = 'ChIJ_xeIOiJ-j4ARBaKTfr3eEIo'
    ORDER BY id
    LIMIT 1
)
UPDATE scraping_sources ss
SET
    scraper_key = 'eventbrite',
    source_url = 'https://www.eventbrite.com',
    eventbrite_id = '71439459',
    enabled = TRUE,
    metadata = '{}'::jsonb,
    updated_at = NOW()
FROM target_club t
WHERE ss.club_id = t.id
  AND ss.platform = 'eventbrite'::"ScrapingPlatform"
  AND ss.priority = 0;

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com',
    '71439459',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE c.google_place_id = 'ChIJ_xeIOiJ-j4ARBaKTfr3eEIo'
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'eventbrite'::"ScrapingPlatform"
        AND s.priority = 0
  )
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.eventbrite_id = '71439459'
  );
