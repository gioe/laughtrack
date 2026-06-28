-- TASK-3373: Onboard Go Comedy! Improv Theater (Ferndale, MI) via generic Squarespace.
--
-- Go Comedy! is a dedicated improv-comedy theater in Ferndale, MI. Its own
-- Squarespace site (gocomedy.net) publishes its show calendar via the Events
-- collection "Calendar" (events-stacked, type 1, collectionId
-- 55817c98e4b028eba1a302ea) exposed at /api/open/GetItemsByMonth.
--
-- The calendar is ALL comedy: weekly improv (Weekend Finale, All-Star Showdown,
-- Pandamonia), stand-up showcases (Mic Check, Green Card Comedy), student
-- showcase performances (the ticketed "Class Shows" / "Student Showcase" public
-- shows), comedy musicals (Survivor the Musical), and the Detroit Improv
-- Festival. Class REGISTRATIONS live on a separate page, not this calendar, so
-- no comedy title filter is needed -- onboard the whole Events collection.
--
-- No net-new scraper: the existing generic `squarespace` scraper reads
-- source_url as the full GetItemsByMonth endpoint (collectionId in the query)
-- and fetches the current month plus the next two. Verified 41 shows, each
-- show_page_url on the venue's own /calendar pages.
--
-- Idempotent (re-runs nightly via bin/migrate): INSERT ... WHERE NOT EXISTS +
-- guarded UPDATE, matched on google_place_id OR (lower(name)).

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
    'Go Comedy! Improv Theater',
    '261 E 9 Mile Rd',
    'https://www.gocomedy.net/',
    '48220',
    'America/Detroit',
    TRUE,
    'Ferndale',
    'MI',
    'active',
    'club',
    'ChIJfapxGP3OJIgRcAWEhI9dIao'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJfapxGP3OJIgRcAWEhI9dIao'
        OR lower(name) = lower('Go Comedy! Improv Theater')
);

UPDATE clubs
   SET address = '261 E 9 Mile Rd',
       website = 'https://www.gocomedy.net/',
       zip_code = '48220',
       timezone = 'America/Detroit',
       visible = TRUE,
       city = 'Ferndale',
       state = 'MI',
       status = 'active',
       club_type = 'club',
       google_place_id = COALESCE(google_place_id, 'ChIJfapxGP3OJIgRcAWEhI9dIao')
 WHERE google_place_id = 'ChIJfapxGP3OJIgRcAWEhI9dIao'
    OR lower(name) = lower('Go Comedy! Improv Theater');

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
    'squarespace'::"ScrapingPlatform",
    'squarespace',
    'https://www.gocomedy.net/api/open/GetItemsByMonth?collectionId=55817c98e4b028eba1a302ea',
    0,
    TRUE,
    '{}'::jsonb
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJfapxGP3OJIgRcAWEhI9dIao'
        OR lower(c.name) = lower('Go Comedy! Improv Theater'))
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.platform = 'squarespace'::"ScrapingPlatform"
          AND s.priority = 0
   );

UPDATE scraping_sources s
   SET scraper_key = 'squarespace',
       source_url = 'https://www.gocomedy.net/api/open/GetItemsByMonth?collectionId=55817c98e4b028eba1a302ea',
       enabled = TRUE,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.platform = 'squarespace'::"ScrapingPlatform"
   AND s.priority = 0
   AND (c.google_place_id = 'ChIJfapxGP3OJIgRcAWEhI9dIao'
        OR lower(c.name) = lower('Go Comedy! Improv Theater'));
