-- Onboard validated high-confidence Google Places comedy-club candidates from
-- the 19103 / 100-mile discovery sweep — TASK-3563.
--
-- Discovery source: Google Places primary_type=comedy_club, deduped against the
-- existing DB by place id/name/address. These three candidates were validated
-- against existing generic scrapers without adding scraper code:
--
-- * The N Crowd — Humanitix host page scraped by `json_ld`:
--   https://events.humanitix.com/host/the-n-crowd
--   Live validation on 2026-07-02 returned 11 future shows.
-- * Laughing Stock Comedy Club — site homepage JSON-LD scraped by `json_ld`:
--   https://www.laughingstockcc.com/
--   Live validation on 2026-07-02 returned 3 future shows.
-- * Brooklyn Comedy Collective — Squarespace events collection scraped by
--   `squarespace`:
--   https://www.brooklyncomedy.com/api/open/GetItemsByMonth?collectionId=5a94518324a69489a755b5d9
--   Live validation on 2026-07-02 returned 101 future shows.
--
-- After this migration is deployed, run:
--   cd apps/scraper && make scrape-club CLUB='The N Crowd'
--   cd apps/scraper && make scrape-club CLUB='Laughing Stock Comedy Club'
--   cd apps/scraper && make scrape-club CLUB='Brooklyn Comedy Collective'

INSERT INTO clubs (
    name, address, website, city, state, zip_code, phone_number,
    latitude, longitude, timezone, country, club_type, google_place_id,
    visible, status
)
SELECT
    'The N Crowd',
    'At Sawubona Creativity Project, 1626 Passyunk Ave, Philadelphia, PA 19148, USA',
    'https://www.phillyncrowd.com/',
    'Philadelphia', 'PA', '19148', '(215) 253-4276',
    39.9293795, -75.16434,
    'America/New_York', 'US', 'club',
    'ChIJs84JlYfIxokRSi0i_-Vg82Y',
    TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJs84JlYfIxokRSi0i_-Vg82Y'
       OR name = 'The N Crowd'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'json_ld',
    'https://events.humanitix.com/host/the-n-crowd',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJs84JlYfIxokRSi0i_-Vg82Y' OR c.name = 'The N Crowd')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'json_ld'
  );

INSERT INTO clubs (
    name, address, website, city, state, zip_code, phone_number,
    latitude, longitude, timezone, country, club_type, google_place_id,
    visible, status
)
SELECT
    'Laughing Stock Comedy Club',
    '604 Station Rd, Grantville, PA 17028, USA',
    'https://www.laughingstockcc.com/',
    'Grantville', 'PA', '17028', '(646) 387-0996',
    40.3803703, -76.6644409,
    'America/New_York', 'US', 'club',
    'ChIJaUIa3syxyIkRCUbHTrRQrQw',
    TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJaUIa3syxyIkRCUbHTrRQrQw'
       OR name = 'Laughing Stock Comedy Club'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'json_ld',
    'https://www.laughingstockcc.com/',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJaUIa3syxyIkRCUbHTrRQrQw' OR c.name = 'Laughing Stock Comedy Club')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'json_ld'
  );

INSERT INTO clubs (
    name, address, website, city, state, zip_code, phone_number,
    latitude, longitude, timezone, country, club_type, google_place_id,
    visible, status
)
SELECT
    'Brooklyn Comedy Collective',
    '167 Graham Ave, Brooklyn, NY 11206, USA',
    'https://www.brooklyncomedy.com/',
    'Brooklyn', 'NY', '11206', '(917) 593-3843',
    40.7077178, -73.9436219,
    'America/New_York', 'US', 'club',
    'ChIJVVWIvFlZwokRCb91vYtPZjA',
    TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJVVWIvFlZwokRCb91vYtPZjA'
       OR name = 'Brooklyn Comedy Collective'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'squarespace',
    'https://www.brooklyncomedy.com/api/open/GetItemsByMonth?collectionId=5a94518324a69489a755b5d9',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJVVWIvFlZwokRCb91vYtPZjA' OR c.name = 'Brooklyn Comedy Collective')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'squarespace'
  );
