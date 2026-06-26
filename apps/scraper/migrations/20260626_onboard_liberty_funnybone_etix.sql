-- TASK-3342: Onboard Liberty Funny Bone (Liberty Township, OH) via etix.
--
-- Discovered near Cincinnati 45202 (TASK-3295). A Funny Bone national-chain
-- club with a packed weekly stand-up calendar — distinct from the existing
-- Columbus/Cleveland/Dayton rows. Confirmed comedy + platform live (2026-06-26):
-- liberty.funnybone.com/shows/ serves the Rockhouse Partners / Etix event widget
-- (rockhouse markup, 282 etix.com/ticket links, real comedian titles: Maurice
-- Benard, Open Mic, ...).
--
-- Platform is etix via the venue's OWN Rockhouse public page — the same shape as
-- the working Columbus/Dayton Funny Bone etix sources. Because the source_url
-- host is liberty.funnybone.com (not etix.com), the etix scraper routes through
-- its Rockhouse-public-source path (_is_rockhouse_public_url) — no
-- _FUNNY_BONE_FALLBACKS entry or etix venue_id needed.
--
-- NOTE: the etix path is DataDome-403'd on residential IPs and only scrapes
-- successfully in GHA (residential proxy + playwright fallback) — see convention
-- #241. The source was browser-verified rich above; the live N>0 scrape is
-- deferred to the post-merge nightly GHA run (criterion 10929).
--
-- visible=TRUE (fixed venue). google_place_id is a real Google id; idempotency
-- matches on it or on (lower(name), lower(city), state).

INSERT INTO clubs (
    name,
    address,
    website,
    zip_code,
    timezone,
    visible,
    city,
    state,
    country,
    status,
    club_type,
    google_place_id
)
SELECT
    'Liberty Funny Bone',
    '7518 Bales St',
    'https://liberty.funnybone.com/',
    '45069',
    'America/New_York',
    TRUE,
    'Liberty Township',
    'OH',
    'US',
    'active',
    'club',
    'ChIJQyR2-j9aQIgRD0Qo2R4qZp4'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJQyR2-j9aQIgRD0Qo2R4qZp4'
        OR (lower(name) = lower('Liberty Funny Bone') AND lower(city) = lower('Liberty Township') AND state = 'OH')
);

UPDATE clubs
   SET address = '7518 Bales St',
       website = 'https://liberty.funnybone.com/',
       zip_code = '45069',
       timezone = 'America/New_York',
       visible = TRUE,
       city = 'Liberty Township',
       state = 'OH',
       country = 'US',
       status = 'active',
       club_type = 'club',
       google_place_id = COALESCE(google_place_id, 'ChIJQyR2-j9aQIgRD0Qo2R4qZp4')
 WHERE google_place_id = 'ChIJQyR2-j9aQIgRD0Qo2R4qZp4'
    OR (lower(name) = lower('Liberty Funny Bone') AND lower(city) = lower('Liberty Township') AND state = 'OH');

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    priority,
    enabled
)
SELECT
    c.id,
    'etix'::"ScrapingPlatform",
    'etix',
    'https://liberty.funnybone.com/shows/',
    0,
    TRUE
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJQyR2-j9aQIgRD0Qo2R4qZp4'
        OR (lower(c.name) = lower('Liberty Funny Bone') AND lower(c.city) = lower('Liberty Township') AND c.state = 'OH'))
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.scraper_key = 'etix'
   );

UPDATE scraping_sources s
   SET platform = 'etix'::"ScrapingPlatform",
       source_url = 'https://liberty.funnybone.com/shows/',
       priority = 0,
       enabled = TRUE,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.scraper_key = 'etix'
   AND (c.google_place_id = 'ChIJQyR2-j9aQIgRD0Qo2R4qZp4'
        OR (lower(c.name) = lower('Liberty Funny Bone') AND lower(c.city) = lower('Liberty Township') AND c.state = 'OH'));
