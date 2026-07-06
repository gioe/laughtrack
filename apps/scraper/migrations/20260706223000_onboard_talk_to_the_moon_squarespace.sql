-- TASK-3609: Onboard Talk to the Moon Comedy Club via generic Squarespace.
--
-- Talk to the Moon is a dedicated comedy club in Pensacola, FL. Its /shows
-- page is a Squarespace products collection (collectionId
-- 68a229e1e17d4b00ad31c2e3): the classic GetItemsByMonth API returns [] for
-- this collection, while /shows?format=json returns store products whose titles
-- carry the show date. Configure collection_type=products so the scraper reads
-- the collection page JSON and parses product titles/body copy.
--
-- Verified live before onboarding: 7 future shows from the products source.

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
    club_type
)
SELECT
    'Talk to the Moon Comedy Club',
    '500 East Heinberg Street',
    'https://www.talktothemooncomedyclub.com',
    '32502',
    'America/Chicago',
    TRUE,
    'Pensacola',
    'FL',
    'active',
    'club'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE lower(name) = lower('Talk to the Moon Comedy Club')
);

UPDATE clubs
   SET address = '500 East Heinberg Street',
       website = 'https://www.talktothemooncomedyclub.com',
       zip_code = '32502',
       timezone = 'America/Chicago',
       visible = TRUE,
       city = 'Pensacola',
       state = 'FL',
       status = 'active',
       club_type = 'club'
 WHERE lower(name) = lower('Talk to the Moon Comedy Club');

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
    'https://www.talktothemooncomedyclub.com/shows?collectionId=68a229e1e17d4b00ad31c2e3',
    0,
    TRUE,
    jsonb_build_object('collection_type', 'products')
  FROM clubs c
 WHERE lower(c.name) = lower('Talk to the Moon Comedy Club')
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.platform = 'squarespace'::"ScrapingPlatform"
          AND s.priority = 0
   );

UPDATE scraping_sources s
   SET scraper_key = 'squarespace',
       source_url = 'https://www.talktothemooncomedyclub.com/shows?collectionId=68a229e1e17d4b00ad31c2e3',
       enabled = TRUE,
       metadata = jsonb_build_object('collection_type', 'products'),
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.platform = 'squarespace'::"ScrapingPlatform"
   AND s.priority = 0
   AND lower(c.name) = lower('Talk to the Moon Comedy Club');
