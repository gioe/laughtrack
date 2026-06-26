-- TASK-3315: Onboard Funny Bone Comedy Club - St. Louis (Westport) via the new
-- StandUp Media scraper.
--
-- The Westport Funny Bone (stlouisfunnybone.com) is a national-chain comedy club
-- confirmed hosting stand-up (Tom Shillue, Joe List, Adam Ferrara, T.J. Miller,
-- ...). The chain's old {city}.funnybone.com/shows/ etix subdomains are dead;
-- the venue sites are now thin front-ends over the StandUp Media reservation API
-- (apireservation.standupmedia.com), a self-hosted ASP.NET platform shared
-- across the Funny Bone / Levity Entertainment network. The generic standup_media
-- scraper (TASK-3315) fetches GetAllShows/{location_id}/false/{dbname} and
-- de-duplicates the per-section rows into one show per ShowID.
--
-- Venue API coordinates (from the site's `var locationid` / `var dbname`):
--   standup_media_location_id = 718bd264-309b-4fa0-a6fa-0b93455f88d0
--   standup_media_dbname      = stlouis_prod
--
-- google_place_id is left NULL: the discovery hint was a placeholder
-- ("FUNNYBONE_WESTPORT"), not a real Google place id. Idempotency matches on
-- (lower(name), lower(city), state) instead.
--
-- visible=TRUE (fixed venue). The reservation API needs no anti-bot handling.

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
    club_type
)
SELECT
    'Funny Bone Comedy Club - St. Louis (Westport)',
    '614 Westport Plaza Dr',
    'https://stlouisfunnybone.com/',
    '63146',
    'America/Chicago',
    TRUE,
    'Maryland Heights',
    'MO',
    'US',
    'active',
    'club'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE lower(name) = lower('Funny Bone Comedy Club - St. Louis (Westport)')
       AND lower(city) = lower('Maryland Heights')
       AND state = 'MO'
);

UPDATE clubs
   SET address = '614 Westport Plaza Dr',
       website = 'https://stlouisfunnybone.com/',
       zip_code = '63146',
       timezone = 'America/Chicago',
       visible = TRUE,
       country = 'US',
       status = 'active',
       club_type = 'club'
 WHERE lower(name) = lower('Funny Bone Comedy Club - St. Louis (Westport)')
   AND lower(city) = lower('Maryland Heights')
   AND state = 'MO';

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
    'standup_media',
    'https://stlouisfunnybone.com/stlouis/events',
    0,
    TRUE,
    '{"standup_media_location_id": "718bd264-309b-4fa0-a6fa-0b93455f88d0", "standup_media_dbname": "stlouis_prod"}'::jsonb
  FROM clubs c
 WHERE lower(c.name) = lower('Funny Bone Comedy Club - St. Louis (Westport)')
   AND lower(c.city) = lower('Maryland Heights')
   AND c.state = 'MO'
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.scraper_key = 'standup_media'
   );

UPDATE scraping_sources s
   SET platform = 'custom'::"ScrapingPlatform",
       source_url = 'https://stlouisfunnybone.com/stlouis/events',
       priority = 0,
       enabled = TRUE,
       metadata = '{"standup_media_location_id": "718bd264-309b-4fa0-a6fa-0b93455f88d0", "standup_media_dbname": "stlouis_prod"}'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.scraper_key = 'standup_media'
   AND lower(c.name) = lower('Funny Bone Comedy Club - St. Louis (Westport)')
   AND lower(c.city) = lower('Maryland Heights')
   AND c.state = 'MO';
