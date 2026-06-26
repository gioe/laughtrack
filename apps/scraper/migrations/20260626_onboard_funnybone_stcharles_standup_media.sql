-- TASK-3316: Onboard Funny Bone Comedy Club - Streets of St. Charles
-- (St. Charles, MO) via the StandUp Media scraper.
--
-- The St. Charles Funny Bone (stlouisfunnybone.com/streets-of-saint-charles) is
-- the second metro St. Louis Funny Bone, distinct from Westport (TASK-3315).
-- Confirmed comedy: GetAllShows returns 146 stand-up shows (Adam Hunter,
-- Brendan Eyre, Dale Jones, Bobby Jaycox, ...). Same platform as Westport —
-- StandUp Media (apireservation.standupmedia.com) — but its OWN coordinates:
--   standup_media_location_id = 154e9304-d10c-483c-b5d6-c8a323483da5
--   standup_media_dbname      = stcharles_prod
-- (read from the /stcharles/events page's var locationid / var dbname; verified
-- live — the location_id resolves to 146 shows, db stcharles_prod.)
--
-- Uses the generic standup_media scraper (TASK-3315), no new code. google_place_id
-- left NULL (the discovery hint was a placeholder "FUNNYBONE_STCHARLES"); idempotency
-- matches on (lower(name), lower(city), state). visible=TRUE (fixed venue).

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
    'Funny Bone Comedy Club - Streets of St. Charles',
    '1520 S 5th St',
    'https://stlouisfunnybone.com/streets-of-saint-charles',
    '63303',
    'America/Chicago',
    TRUE,
    'St. Charles',
    'MO',
    'US',
    'active',
    'club'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE lower(name) = lower('Funny Bone Comedy Club - Streets of St. Charles')
       AND lower(city) = lower('St. Charles')
       AND state = 'MO'
);

UPDATE clubs
   SET address = '1520 S 5th St',
       website = 'https://stlouisfunnybone.com/streets-of-saint-charles',
       zip_code = '63303',
       timezone = 'America/Chicago',
       visible = TRUE,
       country = 'US',
       status = 'active',
       club_type = 'club'
 WHERE lower(name) = lower('Funny Bone Comedy Club - Streets of St. Charles')
   AND lower(city) = lower('St. Charles')
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
    'https://stlouisfunnybone.com/stcharles/events',
    0,
    TRUE,
    '{"standup_media_location_id": "154e9304-d10c-483c-b5d6-c8a323483da5", "standup_media_dbname": "stcharles_prod"}'::jsonb
  FROM clubs c
 WHERE lower(c.name) = lower('Funny Bone Comedy Club - Streets of St. Charles')
   AND lower(c.city) = lower('St. Charles')
   AND c.state = 'MO'
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.scraper_key = 'standup_media'
   );

UPDATE scraping_sources s
   SET platform = 'custom'::"ScrapingPlatform",
       source_url = 'https://stlouisfunnybone.com/stcharles/events',
       priority = 0,
       enabled = TRUE,
       metadata = '{"standup_media_location_id": "154e9304-d10c-483c-b5d6-c8a323483da5", "standup_media_dbname": "stcharles_prod"}'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.scraper_key = 'standup_media'
   AND lower(c.name) = lower('Funny Bone Comedy Club - Streets of St. Charles')
   AND lower(c.city) = lower('St. Charles')
   AND c.state = 'MO';
