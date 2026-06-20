-- TASK-3025: Onboard Park Theatre (Holland, MI) via the new Ludus scraper.
--
-- Park Theatre (parktheatreholland.org) is a mixed-use live-music venue/theater
-- that tickets via Ludus (ludus.com, formerly Tixato), subdomain
-- 'parktheatreholland'. The venue's own Spacecrafted site only embeds the Ludus
-- widget, so we scrape the Ludus subdomain directly. The discovery hint
-- 'comedy.tickets' was a misfire — the real platform is Ludus.
--
-- Ludus is multi-venue, so scraper_key='ludus' is generic. Comedy shows carry
-- the venue-specific category id 468 in the embed's data-event-categories; the
-- &category_id= URL param does not server-side filter, so the scraper filters
-- client-side on that tag and layers the shared comedy keyword/comedian filter
-- to drop venue mis-tags (e.g. a 'Radiohead Performed by Android Paranoid'
-- tribute band mis-tagged 468). comedy_filter is enabled for that reason.
--
-- visible=TRUE (fixed venue). Cloudflare managed challenge is cleared by the
-- scraper's curl_cffi impersonation.
--
-- Idempotent: matches on google_place_id or lowercase name, and on
-- (club_id, scraper_key) for the source.

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
    'Park Theatre',
    '248 S River Ave',
    'https://parktheatreholland.org/',
    '49423',
    'America/Detroit',
    TRUE,
    'Holland',
    'MI',
    'active',
    'club',
    'ChIJn8cCVrfyGYgRzUzahhTdGq4'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJn8cCVrfyGYgRzUzahhTdGq4'
        OR lower(name) = lower('Park Theatre')
);

UPDATE clubs
   SET address = '248 S River Ave',
       website = 'https://parktheatreholland.org/',
       zip_code = '49423',
       timezone = 'America/Detroit',
       visible = TRUE,
       city = 'Holland',
       state = 'MI',
       status = 'active',
       club_type = 'club',
       google_place_id = COALESCE(google_place_id, 'ChIJn8cCVrfyGYgRzUzahhTdGq4')
 WHERE google_place_id = 'ChIJn8cCVrfyGYgRzUzahhTdGq4'
    OR lower(name) = lower('Park Theatre');

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
    'ludus',
    'https://parktheatreholland.ludus.com/',
    0,
    TRUE,
    '{"ludus_subdomain": "parktheatreholland", "comedy_category_id": "468", "comedy_filter": true}'::jsonb
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJn8cCVrfyGYgRzUzahhTdGq4'
        OR lower(c.name) = lower('Park Theatre'))
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.scraper_key = 'ludus'
   );

UPDATE scraping_sources s
   SET platform = 'custom'::"ScrapingPlatform",
       source_url = 'https://parktheatreholland.ludus.com/',
       priority = 0,
       enabled = TRUE,
       metadata = '{"ludus_subdomain": "parktheatreholland", "comedy_category_id": "468", "comedy_filter": true}'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.scraper_key = 'ludus'
   AND (c.google_place_id = 'ChIJn8cCVrfyGYgRzUzahhTdGq4'
        OR lower(c.name) = lower('Park Theatre'));
