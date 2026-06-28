-- TASK-3378: Onboard Kesha's Comedy House (Eastpointe, MI) via the generic
-- Shopify scraper.
--
-- Kesha's Comedy House is a fixed Eastpointe comedy venue that sells tickets as
-- Shopify products (store efd4qj-cg.myshopify.com, front-ended at
-- keshascomedyhouse.com). There is no /collections/shows; the dated comedy
-- products live in the root catalog, so source_url is the BASE DOMAIN and the
-- scraper fetches /products.json (whole catalog) + tag/date filtering.
--
-- This is an ad-hoc Shopify store: each show's date is the M/D prefix of the
-- product TITLE (e.g. "6/28 Spoken Laugh Lounge"), handles are stale/reused, and
-- the showtime is published only on the flyer IMAGE — no clock time anywhere in
-- the JSON. metadata.default_show_time='20:00' supplies the missing time on the
-- Format C path (8pm, the venue's standard comedy slot) so dated shows are kept
-- instead of dropped. Undated products (merch t-shirt, recurring "Karaoke
-- Wednesdays", date-less specials) carry no parseable date and drop naturally.
--
-- platform='shopify', scraper_key='shopify' (generic — no Python venue code).
--
-- Idempotent (re-runs nightly via bin/migrate): INSERT ... WHERE NOT EXISTS +
-- guarded UPDATE, matched on google_place_id OR (lower(name)); the
-- scraping_sources guard keys on the (club_id, platform, priority) unique
-- constraint.

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
    'Kesha''s Comedy House',
    '20958 Gratiot Ave',
    'https://keshascomedyhouse.com/',
    '48021',
    'America/Detroit',
    TRUE,
    'Eastpointe',
    'MI',
    'active',
    'club',
    'ChIJWUsvUQDXJIgRkjxlbmT7psg'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJWUsvUQDXJIgRkjxlbmT7psg'
        OR lower(name) = lower('Kesha''s Comedy House')
);

UPDATE clubs
   SET address = '20958 Gratiot Ave',
       website = 'https://keshascomedyhouse.com/',
       zip_code = '48021',
       timezone = 'America/Detroit',
       visible = TRUE,
       city = 'Eastpointe',
       state = 'MI',
       status = 'active',
       club_type = 'club',
       google_place_id = COALESCE(google_place_id, 'ChIJWUsvUQDXJIgRkjxlbmT7psg')
 WHERE google_place_id = 'ChIJWUsvUQDXJIgRkjxlbmT7psg'
    OR lower(name) = lower('Kesha''s Comedy House');

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
    'shopify'::"ScrapingPlatform",
    'shopify',
    'https://keshascomedyhouse.com',
    0,
    TRUE,
    jsonb_build_object('default_show_time', '20:00')
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJWUsvUQDXJIgRkjxlbmT7psg'
        OR lower(c.name) = lower('Kesha''s Comedy House'))
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.platform = 'shopify'::"ScrapingPlatform"
          AND s.priority = 0
   );

UPDATE scraping_sources s
   SET scraper_key = 'shopify',
       source_url = 'https://keshascomedyhouse.com',
       enabled = TRUE,
       metadata = jsonb_build_object('default_show_time', '20:00'),
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.platform = 'shopify'::"ScrapingPlatform"
   AND s.priority = 0
   AND (c.google_place_id = 'ChIJWUsvUQDXJIgRkjxlbmT7psg'
        OR lower(c.name) = lower('Kesha''s Comedy House'));
