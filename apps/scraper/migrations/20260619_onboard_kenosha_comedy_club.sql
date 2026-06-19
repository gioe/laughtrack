-- TASK-2978: Onboard Kenosha Comedy Club.
--
-- The venue's domain redirects to Happenings Magazine's Kenosha Comedy Club
-- WordPress category. The standard Tribe Events API is present on that site but
-- returns no events for these shows; current club shows are plain WordPress
-- posts under category 506, parsed by scraper_key='kenosha_comedy_club'.

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
    'Kenosha Comedy Club',
    '5125 6th Ave',
    'https://www.kenoshacomedyclub.com/',
    '53140',
    'America/Chicago',
    TRUE,
    'Kenosha',
    'WI',
    'active',
    'club',
    'ChIJVVUVm2BeBYgR2m_s9T1cWlc'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJVVUVm2BeBYgR2m_s9T1cWlc'
        OR lower(name) = lower('Kenosha Comedy Club')
);

UPDATE clubs
   SET address = '5125 6th Ave',
       website = 'https://www.kenoshacomedyclub.com/',
       zip_code = '53140',
       timezone = 'America/Chicago',
       visible = TRUE,
       city = 'Kenosha',
       state = 'WI',
       status = 'active',
       club_type = 'club',
       google_place_id = COALESCE(google_place_id, 'ChIJVVUVm2BeBYgR2m_s9T1cWlc')
 WHERE google_place_id = 'ChIJVVUVm2BeBYgR2m_s9T1cWlc'
    OR lower(name) = lower('Kenosha Comedy Club');

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
    'kenosha_comedy_club',
    'https://happeningsmag.com/wp-json/wp/v2/posts?categories=506&per_page=20&_fields=id,date,modified,link,title,excerpt,categories',
    0,
    TRUE,
    '{}'::jsonb
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJVVUVm2BeBYgR2m_s9T1cWlc'
        OR lower(c.name) = lower('Kenosha Comedy Club'))
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.scraper_key = 'kenosha_comedy_club'
   );

UPDATE scraping_sources s
   SET platform = 'custom'::"ScrapingPlatform",
       source_url = 'https://happeningsmag.com/wp-json/wp/v2/posts?categories=506&per_page=20&_fields=id,date,modified,link,title,excerpt,categories',
       priority = 0,
       enabled = TRUE,
       metadata = '{}'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.scraper_key = 'kenosha_comedy_club'
   AND (c.google_place_id = 'ChIJVVUVm2BeBYgR2m_s9T1cWlc'
        OR lower(c.name) = lower('Kenosha Comedy Club'));
