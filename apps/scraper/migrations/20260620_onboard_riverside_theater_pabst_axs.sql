-- TASK-3033: Onboard The Riverside Theater (Milwaukee) on the new pabst_axs scraper.
--
-- The Riverside Theater is a Pabst Theater Group room (pabsttheater.org), ticketed
-- via AXS (skin=pabst). Its venue page is plain server-rendered HTML listing every
-- upcoming show as a div.eventItem card; the new scraper_key='pabst_axs' parses
-- those cards (title + AXS id + date-in-thumbnail-filename) without touching the
-- DataDome-protected axs.com detail pages.
--
-- The room is music-dominated (~5-7 comedy acts among ~20 events), so the source
-- opts into the shared comedy filter: comedy_filter keeps a title with a comedy
-- keyword OR a known comedian above the popularity floor; comedy_title_allowlist
-- force-keeps the comedian-name acts the keyword filter misses (e.g. "Wait Wait…
-- Don't Tell Me!", "Ben Schwartz & Friends", "Anthony Jeselnik", "Matt Mathews",
-- the Hasan Minhaj / Ronny Chieng wordplay title).
--
-- Idempotent: keyed on google_place_id (falls back to case-insensitive name).

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
    'The Riverside Theater',
    '116 W Wisconsin Ave',
    'https://pabsttheater.org/venues/the-riverside-theater/',
    '53203',
    'America/Chicago',
    TRUE,
    'Milwaukee',
    'WI',
    'active',
    'theater',
    'ChIJa5H5_wkZBYgRUsC7EMJVvh0'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJa5H5_wkZBYgRUsC7EMJVvh0'
        OR lower(name) = lower('The Riverside Theater')
);

UPDATE clubs
   SET address = '116 W Wisconsin Ave',
       website = 'https://pabsttheater.org/venues/the-riverside-theater/',
       zip_code = '53203',
       timezone = 'America/Chicago',
       visible = TRUE,
       city = 'Milwaukee',
       state = 'WI',
       status = 'active',
       club_type = 'theater',
       google_place_id = COALESCE(google_place_id, 'ChIJa5H5_wkZBYgRUsC7EMJVvh0')
 WHERE google_place_id = 'ChIJa5H5_wkZBYgRUsC7EMJVvh0'
    OR lower(name) = lower('The Riverside Theater');

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
    'pabst_axs',
    'https://pabsttheater.org/venues/the-riverside-theater/',
    0,
    TRUE,
    '{"default_show_time": "19:00", "comedy_filter": true, "comedy_title_allowlist": ["wait wait", "hasan", "ronny chieng", "anthony jeselnik", "ben schwartz", "matt mathews"]}'::jsonb
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJa5H5_wkZBYgRUsC7EMJVvh0'
        OR lower(c.name) = lower('The Riverside Theater'))
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.scraper_key = 'pabst_axs'
   );

UPDATE scraping_sources s
   SET platform = 'custom'::"ScrapingPlatform",
       source_url = 'https://pabsttheater.org/venues/the-riverside-theater/',
       priority = 0,
       enabled = TRUE,
       metadata = '{"default_show_time": "19:00", "comedy_filter": true, "comedy_title_allowlist": ["wait wait", "hasan", "ronny chieng", "anthony jeselnik", "ben schwartz", "matt mathews"]}'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.scraper_key = 'pabst_axs'
   AND (c.google_place_id = 'ChIJa5H5_wkZBYgRUsC7EMJVvh0'
        OR lower(c.name) = lower('The Riverside Theater'));
