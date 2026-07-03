-- Onboard validated high-confidence Google Places comedy-club candidates from
-- the 19103 / 100-mile discovery sweep — TASK-3563.
--
-- Discovery source: Google Places primary_type=comedy_club, deduped against the
-- existing DB by place id/name/address. These candidates were validated
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
-- * Meadowlands Comedy Club — event detail pages scraped by `json_ld`
--   detail-fetch mode:
--   https://meadowlandscomedyclub.com/
--   Live validation on 2026-07-02 returned 2 future shows.
-- * High Line Comedy Club — Eventbrite organizer id 91898788783, configured in
--   single-club mode so the venue endpoint 404 falls back to organizer events
--   without organizer-mode venue upserts:
--   https://www.eventbrite.com
--   Live validation on 2026-07-02 returned 23 future shows.
-- * BATSU! — Tock business page rendered by the generic `tock` scraper:
--   https://www.exploretock.com/batsunyc
--   Live validation on 2026-07-02 returned 240 future shows.
-- * Give A Hoot Comedy Club NJ — SeatEngine white-label event pages scraped
--   by the generic `seatengine_web` scraper:
--   https://www.giveahootcomedyclubnj.com/
--   Live validation on 2026-07-02 returned 6 future shows.
-- * Colonial Comedy — native Wix Events API via the generic `wix_events`
--   scraper, which returns the site's two public upcoming comedy shows without
--   a compId:
--   https://www.colonialcomedy.com/
--   Live validation on 2026-07-02 returned 2 future shows.
-- * Captain Kirk's Comedy Lounge — Eventbrite organizer id 58553141833,
--   configured in single-club mode:
--   https://www.eventbrite.com
--   Live validation on 2026-07-02 returned 4 future shows.
-- * Sheba's Speakeasy Comedy Club — Eventbrite organizer id 77390385933,
--   configured in single-club mode:
--   https://www.eventbrite.com
--   Live validation on 2026-07-02 returned 38 future shows.
-- * East Village Stand Up Comedy — Eventbrite organizer id 10025720196,
--   configured in single-club mode:
--   https://www.eventbrite.com
--   Live validation on 2026-07-02 returned 25 future shows.
-- * The Comedy Works — TicketSpice form scraped by the generic
--   `ticketspice` scraper:
--   https://comedyworksbristol.ticketspice.com/comedyweekendlaughsjuly10-11
--   Live validation on 2026-07-02 returned 1 future show.
-- * Comedy Explosion — native Wix Events API via the generic `wix_events`
--   scraper:
--   https://thecomedyexplosion.com/
--   Live validation on 2026-07-03 returned 1 future show.
-- * The Lab — Eventbrite organizer id 26956500819 with metadata filters to
--   keep show titles and drop classes:
--   https://www.eventbrite.com
--   Live validation on 2026-07-03 returned 4 future shows.
-- * Upright Citizens Brigade Theatre — WP Grid Builder location-filtered
--   cards scraped by the existing `ucb` scraper:
--   https://ucbcomedy.com/shows/
--   Live validation on 2026-07-03 returned 62 Mainstage shows and 10 Upstairs
--   shows using metadata.location_slug values `nyc-mainstage` and
--   `nyc-upstairs`.
-- * Stones Comedy Club — Eventbrite organizer id 33078829209, configured in
--   single-club mode:
--   https://www.eventbrite.com
--   Live validation on 2026-07-03 returned 52 future shows.
-- * Sesh Comedy — FullCalendar JSON feed scraped by the generic
--   `fullcalendar_json` scraper:
--   https://www.seshcomedy.com/feed.php
--   Live validation on 2026-07-03 returned 42 future shows.
-- * The Second City New York — Second City platform GraphQL/entityResolver
--   scraper with metadata.location_slug `new-york` and NY venue-name filters:
--   https://www.secondcity.com/shows/new-york/
--   Live validation on 2026-07-03 returned 3 future shows.
-- * Comedy Cabaret Comedy Club — PatronBase productions RSS scraped by the
--   generic `patronbase_rss` scraper:
--   https://us.patronbase.com/_ComedyCabaret/Productions/RSS
--   Live validation on 2026-07-03 returned 5 future shows.
-- * Rhino Comedy — Squarespace products-mode scraper with ordinal/yearless
--   product date parsing and metadata excludes for classes/workshops/closures:
--   https://www.rhinoimprov.com/tickets
--   Live validation on 2026-07-03 returned 18 future shows.
-- * Flop House Comedy Club — site-specific JSON feeds discovered in the app
--   bundle (`/venues.json` -> `/venues/{id}_events.json`):
--   https://www.flophousecomedy.com/
--   Live validation on 2026-07-03 returned 57 future shows.
-- * The PIT — WordPress events RSS item links to detail pages with schema.org
--   Event/subEvent JSON-LD, scraped by `json_ld` detail-fetch feed mode:
--   https://thepit-nyc.com/events/feed/
--   Live validation on 2026-07-03 returned 32 future shows.
--
-- After this migration is deployed, run:
--   cd apps/scraper && make scrape-club CLUB='The N Crowd'
--   cd apps/scraper && make scrape-club CLUB='Laughing Stock Comedy Club'
--   cd apps/scraper && make scrape-club CLUB='Brooklyn Comedy Collective'
--   cd apps/scraper && make scrape-club CLUB='Meadowlands Comedy Club'
--   cd apps/scraper && make scrape-club CLUB='High Line Comedy Club'
--   cd apps/scraper && make scrape-club CLUB='BATSU!'
--   cd apps/scraper && make scrape-club CLUB='Give A Hoot Comedy Club NJ'
--   cd apps/scraper && make scrape-club CLUB='Colonial Comedy'
--   cd apps/scraper && make scrape-club CLUB='Captain Kirk''s Comedy Lounge'
--   cd apps/scraper && make scrape-club CLUB='Sheba''s Speakeasy Comedy Club'
--   cd apps/scraper && make scrape-club CLUB='East Village Stand Up Comedy'
--   cd apps/scraper && make scrape-club CLUB='The Comedy Works'
--   cd apps/scraper && make scrape-club CLUB='Comedy Explosion'
--   cd apps/scraper && make scrape-club CLUB='The Lab'
--   cd apps/scraper && make scrape-club CLUB='Upright Citizens Brigade Theatre New York'
--   cd apps/scraper && make scrape-club CLUB='Stones Comedy Club'
--   cd apps/scraper && make scrape-club CLUB='Sesh Comedy'
--   cd apps/scraper && make scrape-club CLUB='The Second City New York'
--   cd apps/scraper && make scrape-club CLUB='Comedy Cabaret Comedy Club'
--   cd apps/scraper && make scrape-club CLUB='Rhino Comedy'
--   cd apps/scraper && make scrape-club CLUB='Flop House Comedy Club'
--   cd apps/scraper && make scrape-club CLUB='The PIT'

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
      WHERE s.club_id = c.id
        AND s.platform = 'custom'::"ScrapingPlatform"
        AND s.priority = 0
  );

INSERT INTO clubs (
    name, address, website, city, state, zip_code, phone_number,
    latitude, longitude, timezone, country, club_type, google_place_id,
    visible, status
)
SELECT
    'The Lab',
    '85 E Butler Ave, Ambler, PA 19002, USA',
    'https://www.thelabambler.com/',
    'Ambler', 'PA', '19002', '',
    40.1546752, -75.2219369,
    'America/New_York', 'US', 'club',
    'ChIJgRv5Eqe7xokRNgxFBVzkqRY',
    TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJgRv5Eqe7xokRNgxFBVzkqRY'
       OR (name = 'The Lab' AND city = 'Ambler' AND state = 'PA')
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com',
    '26956500819',
    TRUE,
    0,
    '{"exclude_classes": true, "include_title_patterns": ["N Crowd", "This Week Sucked", "Wednesday Night Improv", "Date Nite", "Howl"]}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJgRv5Eqe7xokRNgxFBVzkqRY' OR (c.name = 'The Lab' AND c.city = 'Ambler' AND c.state = 'PA'))
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'eventbrite'::"ScrapingPlatform"
        AND s.priority = 0
  );

INSERT INTO clubs (
    name, address, website, city, state, zip_code, phone_number,
    latitude, longitude, timezone, country, club_type, google_place_id,
    visible, status
)
SELECT
    'Comedy Explosion',
    '815 N Pottstown Pike, Exton, PA 19341, USA',
    'https://thecomedyexplosion.com/',
    'Exton', 'PA', '19341', '(484) 393-1593',
    40.0566238, -75.6494480,
    'America/New_York', 'US', 'club',
    'ChIJoTL1eJ_7xokRxKP67A-9Aw0',
    TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJoTL1eJ_7xokRxKP67A-9Aw0'
       OR name = 'Comedy Explosion'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'wix_events'::"ScrapingPlatform",
    'wix_events',
    'https://thecomedyexplosion.com/',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJoTL1eJ_7xokRxKP67A-9Aw0' OR c.name = 'Comedy Explosion')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'wix_events'::"ScrapingPlatform"
        AND s.priority = 0
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
      WHERE s.club_id = c.id
        AND s.platform = 'custom'::"ScrapingPlatform"
        AND s.priority = 0
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
      WHERE s.club_id = c.id
        AND s.platform = 'custom'::"ScrapingPlatform"
        AND s.priority = 0
  );

INSERT INTO clubs (
    name, address, website, city, state, zip_code, phone_number,
    latitude, longitude, timezone, country, club_type, google_place_id,
    visible, status
)
SELECT
    'Meadowlands Comedy Club',
    '317 Washington Ave, Carlstadt, NJ 07072, USA',
    'https://www.meadowlandscomedyclub.com/',
    'Carlstadt', 'NJ', '07072', '(201) 893-9777',
    40.8173499, -74.0658562,
    'America/New_York', 'US', 'club',
    'ChIJXdCbldpXwokRfoD0jom327Q',
    TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJXdCbldpXwokRfoD0jom327Q'
       OR name = 'Meadowlands Comedy Club'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'json_ld',
    'https://meadowlandscomedyclub.com/',
    TRUE,
    0,
    '{"detail_fetch": {"url_path_prefix": "/event/"}}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJXdCbldpXwokRfoD0jom327Q' OR c.name = 'Meadowlands Comedy Club')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'custom'::"ScrapingPlatform"
        AND s.priority = 0
  );

INSERT INTO clubs (
    name, address, website, city, state, zip_code, phone_number,
    latitude, longitude, timezone, country, club_type, google_place_id,
    visible, status
)
SELECT
    'High Line Comedy Club',
    '446 W 14th St, New York, NY 10014, USA',
    'https://highlinecomedy.com/',
    'New York', 'NY', '10014', '(646) 543-1878',
    40.7415865, -74.0075955,
    'America/New_York', 'US', 'club',
    'ChIJXfsikHhZwokRxr1XAbft_X8',
    TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJXfsikHhZwokRxr1XAbft_X8'
       OR name = 'High Line Comedy Club'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com',
    '91898788783',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJXfsikHhZwokRxr1XAbft_X8' OR c.name = 'High Line Comedy Club')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'eventbrite'::"ScrapingPlatform"
        AND s.priority = 0
  );

INSERT INTO clubs (
    name, address, website, city, state, zip_code, phone_number,
    latitude, longitude, timezone, country, club_type, google_place_id,
    visible, status
)
SELECT
    'BATSU!',
    '67 1st Ave, New York, NY 10003, USA',
    'https://batsulive.com/',
    'New York', 'NY', '10003', '',
    40.7253441, -73.9872209,
    'America/New_York', 'US', 'club',
    'ChIJ4QKVd5xZwokRKNIH6nKJPAE',
    TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJ4QKVd5xZwokRKNIH6nKJPAE'
       OR name = 'BATSU!'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'tock',
    'https://www.exploretock.com/batsunyc',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJ4QKVd5xZwokRKNIH6nKJPAE' OR c.name = 'BATSU!')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'custom'::"ScrapingPlatform"
        AND s.priority = 0
  );

INSERT INTO clubs (
    name, address, website, city, state, zip_code, phone_number,
    latitude, longitude, timezone, country, club_type, google_place_id,
    visible, status
)
SELECT
    'Give A Hoot Comedy Club NJ',
    '281 Cross Keys Rd, Berlin, NJ 08009, USA',
    'https://www.giveahootcomedyclubnj.com/',
    'Berlin', 'NJ', '08009', '(856) 753-4176',
    39.7865089, -74.9471558,
    'America/New_York', 'US', 'club',
    'ChIJXd-xbnItwYkRuNSn__rA_2o',
    TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJXd-xbnItwYkRuNSn__rA_2o'
       OR name = 'Give A Hoot Comedy Club NJ'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'seatengine_web',
    'https://www.giveahootcomedyclubnj.com/',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJXd-xbnItwYkRuNSn__rA_2o' OR c.name = 'Give A Hoot Comedy Club NJ')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'custom'::"ScrapingPlatform"
        AND s.priority = 0
  );

INSERT INTO clubs (
    name, address, website, city, state, zip_code, phone_number,
    latitude, longitude, timezone, country, club_type, google_place_id,
    visible, status
)
SELECT
    'Colonial Comedy',
    '39 Maple Ave, Morristown, NJ 07960, USA',
    'https://www.colonialcomedy.com/',
    'Morristown', 'NJ', '07960', '(973) 946-8930',
    40.7937068, -74.4810685,
    'America/New_York', 'US', 'club',
    'ChIJn8bwdkSnw4kRzYbWgB3rhO8',
    TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJn8bwdkSnw4kRzYbWgB3rhO8'
       OR name = 'Colonial Comedy'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'wix_events'::"ScrapingPlatform",
    'wix_events',
    'https://www.colonialcomedy.com/',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJn8bwdkSnw4kRzYbWgB3rhO8' OR c.name = 'Colonial Comedy')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'wix_events'::"ScrapingPlatform"
        AND s.priority = 0
  );

INSERT INTO clubs (
    name, address, website, city, state, zip_code, phone_number,
    latitude, longitude, timezone, country, club_type, google_place_id,
    visible, status
)
SELECT
    'Captain Kirk''s Comedy Lounge',
    '1000 Broadway, Brooklyn, NY 11221, USA',
    'https://www.captainkirkscomedylounge.com/',
    'Brooklyn', 'NY', '11221', '(516) 960-3833',
    40.6959272, -73.9337412,
    'America/New_York', 'US', 'club',
    'ChIJvQQs6nlbwokR8Y4g0f5pXZA',
    TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJvQQs6nlbwokR8Y4g0f5pXZA'
       OR name = 'Captain Kirk''s Comedy Lounge'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com',
    '58553141833',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJvQQs6nlbwokR8Y4g0f5pXZA' OR c.name = 'Captain Kirk''s Comedy Lounge')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'eventbrite'::"ScrapingPlatform"
        AND s.priority = 0
  );

INSERT INTO clubs (
    name, address, website, city, state, zip_code, phone_number,
    latitude, longitude, timezone, country, club_type, google_place_id,
    visible, status
)
SELECT
    'Sheba''s Speakeasy Comedy Club',
    '832 8th Avenue, New York, NY 10019, USA',
    'https://shebamason.com/',
    'New York', 'NY', '10019', '(646) 351-2904',
    40.7623663, -73.9857634,
    'America/New_York', 'US', 'club',
    'ChIJFzCDZx1ZwokR0Xbe8D5v1jQ',
    TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJFzCDZx1ZwokR0Xbe8D5v1jQ'
       OR name = 'Sheba''s Speakeasy Comedy Club'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com',
    '77390385933',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJFzCDZx1ZwokR0Xbe8D5v1jQ' OR c.name = 'Sheba''s Speakeasy Comedy Club')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'eventbrite'::"ScrapingPlatform"
        AND s.priority = 0
  );

INSERT INTO clubs (
    name, address, website, city, state, zip_code, phone_number,
    latitude, longitude, timezone, country, club_type, google_place_id,
    visible, status
)
SELECT
    'East Village Stand Up Comedy',
    '174 E 2nd St, New York, NY 10009, USA',
    'https://greatestshowever.com/',
    'New York', 'NY', '10009', '(212) 365-0334',
    40.7226824, -73.9845869,
    'America/New_York', 'US', 'club',
    'ChIJfWiS_xVZwokRwizGl3R3AME',
    TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJfWiS_xVZwokRwizGl3R3AME'
       OR name = 'East Village Stand Up Comedy'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com',
    '10025720196',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJfWiS_xVZwokRwizGl3R3AME' OR c.name = 'East Village Stand Up Comedy')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'eventbrite'::"ScrapingPlatform"
        AND s.priority = 0
  );

INSERT INTO clubs (
    name, address, website, city, state, zip_code, phone_number,
    latitude, longitude, timezone, country, club_type, google_place_id,
    visible, status
)
SELECT
    'The Comedy Works',
    '1320 Newport Rd, Bristol, PA 19007, USA',
    'https://comedyworksbristol.com/',
    'Bristol', 'PA', '19007', '(215) 741-1661',
    40.1047222, -74.8911111,
    'America/New_York', 'US', 'club',
    'ChIJ2WY0G-pNwYkRSA9-Mu25f24',
    TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJ2WY0G-pNwYkRSA9-Mu25f24'
       OR (name = 'The Comedy Works' AND city = 'Bristol' AND state = 'PA')
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'ticketspice',
    'https://comedyworksbristol.ticketspice.com/comedyweekendlaughsjuly10-11',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJ2WY0G-pNwYkRSA9-Mu25f24' OR (c.name = 'The Comedy Works' AND c.city = 'Bristol' AND c.state = 'PA'))
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'custom'::"ScrapingPlatform"
        AND s.priority = 0
  );

INSERT INTO clubs (
    name, address, website, city, state, zip_code, phone_number,
    latitude, longitude, timezone, country, club_type, google_place_id,
    visible, status
)
SELECT
    'Upright Citizens Brigade Theatre New York',
    '242 E 14th St, New York, NY 10003, USA',
    'https://ucbcomedy.com/',
    'New York', 'NY', '10003', '',
    40.7324960, -73.9856657,
    'America/New_York', 'US', 'club',
    'ChIJYwz0-YJZwokR1XOunnE1Pe4',
    TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJYwz0-YJZwokR1XOunnE1Pe4'
       OR (name = 'Upright Citizens Brigade Theatre New York' AND city = 'New York' AND state = 'NY')
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'ucb',
    'https://ucbcomedy.com/shows/',
    TRUE,
    0,
    '{"location_slug": "nyc-mainstage"}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJYwz0-YJZwokR1XOunnE1Pe4' OR (c.name = 'Upright Citizens Brigade Theatre New York' AND c.city = 'New York' AND c.state = 'NY'))
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'custom'::"ScrapingPlatform"
        AND s.priority = 0
  );

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'ucb',
    'https://ucbcomedy.com/shows/',
    TRUE,
    1,
    '{"location_slug": "nyc-upstairs"}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJYwz0-YJZwokR1XOunnE1Pe4' OR (c.name = 'Upright Citizens Brigade Theatre New York' AND c.city = 'New York' AND c.state = 'NY'))
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'custom'::"ScrapingPlatform"
        AND s.priority = 1
  );

INSERT INTO clubs (
    name, address, website, city, state, zip_code, phone_number,
    latitude, longitude, timezone, country, club_type, google_place_id,
    visible, status
)
SELECT
    'Stones Comedy Club',
    '225 E 44th St, New York, NY 10017, USA',
    'https://stonestreetcomedyclub.com/',
    'New York', 'NY', '10017', '(917) 364-6258',
    40.7517163, -73.9722844,
    'America/New_York', 'US', 'club',
    'ChIJV3CtSlJbwokRW6gCgnAFt-E',
    TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJV3CtSlJbwokRW6gCgnAFt-E'
       OR (name = 'Stones Comedy Club' AND city = 'New York' AND state = 'NY')
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com',
    '33078829209',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJV3CtSlJbwokRW6gCgnAFt-E' OR (c.name = 'Stones Comedy Club' AND c.city = 'New York' AND c.state = 'NY'))
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'eventbrite'::"ScrapingPlatform"
        AND s.priority = 0
  );

INSERT INTO clubs (
    name, address, website, city, state, zip_code, phone_number,
    latitude, longitude, timezone, country, club_type, google_place_id,
    visible, status
)
SELECT
    'Sesh Comedy',
    '55 Chrystie St, New York, NY 10002, USA',
    'https://www.seshcomedy.com/',
    'New York', 'NY', '10002', '(201) 898-0759',
    40.7164535, -73.9948933,
    'America/New_York', 'US', 'club',
    'ChIJ59-_Gu5ZwokR7Xc8o5IAtY0',
    TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJ59-_Gu5ZwokR7Xc8o5IAtY0'
       OR (name = 'Sesh Comedy' AND city = 'New York' AND state = 'NY')
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'fullcalendar_json',
    'https://www.seshcomedy.com/feed.php',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJ59-_Gu5ZwokR7Xc8o5IAtY0' OR (c.name = 'Sesh Comedy' AND c.city = 'New York' AND c.state = 'NY'))
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'custom'::"ScrapingPlatform"
        AND s.priority = 0
  );

INSERT INTO clubs (
    name, address, website, city, state, zip_code, phone_number,
    latitude, longitude, timezone, country, club_type, google_place_id,
    visible, status
)
SELECT
    'The Second City New York',
    '64 N 9th St, Brooklyn, NY 11249, USA',
    'https://www.secondcity.com/shows/new-york/',
    'Brooklyn', 'NY', '11249', '',
    40.7207727, -73.9599814,
    'America/New_York', 'US', 'club',
    'ChIJv4cccglZwokRwENgJq6qkXs',
    TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJv4cccglZwokRwENgJq6qkXs'
       OR (name = 'The Second City New York' AND city = 'Brooklyn' AND state = 'NY')
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'up_comedy_club',
    'https://www.secondcity.com/shows/new-york/',
    TRUE,
    0,
    '{
        "location_slug": "new-york",
        "venue_name_contains": [
            "Second City New York Mainstage",
            "The Second City New York Blackbox Theater"
        ]
    }'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJv4cccglZwokRwENgJq6qkXs' OR (c.name = 'The Second City New York' AND c.city = 'Brooklyn' AND c.state = 'NY'))
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'custom'::"ScrapingPlatform"
        AND s.priority = 0
  );

INSERT INTO clubs (
    name, address, website, city, state, zip_code, phone_number,
    latitude, longitude, timezone, country, club_type, google_place_id,
    visible, status
)
SELECT
    'Comedy Cabaret Comedy Club',
    '625 N Main St, Doylestown, PA 18901, USA',
    'https://comedycabaret.com/bucks-county-doylestown/',
    'Doylestown', 'PA', '18901', '',
    40.3251533, -75.1296768,
    'America/New_York', 'US', 'club',
    'ChIJgywfGpgCxIkRvQVpKm08aZg',
    TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJgywfGpgCxIkRvQVpKm08aZg'
       OR (name = 'Comedy Cabaret Comedy Club' AND city = 'Doylestown' AND state = 'PA')
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'patronbase_rss',
    'https://us.patronbase.com/_ComedyCabaret/Productions/RSS',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJgywfGpgCxIkRvQVpKm08aZg' OR (c.name = 'Comedy Cabaret Comedy Club' AND c.city = 'Doylestown' AND c.state = 'PA'))
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'custom'::"ScrapingPlatform"
        AND s.priority = 0
  );

INSERT INTO clubs (
    name, address, website, city, state, zip_code, phone_number,
    latitude, longitude, timezone, country, club_type, google_place_id,
    visible, status
)
SELECT
    'Rhino Comedy',
    '22 Lafayette Ave 2nd Floor, Suffern, NY 10901, USA',
    'https://www.rhinoimprov.com/',
    'Suffern', 'NY', '10901', '',
    41.1163537, -74.1536801,
    'America/New_York', 'US', 'club',
    'ChIJh1wR5JTgwokRtRdGI6Eryto',
    TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJh1wR5JTgwokRtRdGI6Eryto'
       OR (name = 'Rhino Comedy' AND city = 'Suffern' AND state = 'NY')
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'squarespace',
    'https://www.rhinoimprov.com/tickets',
    TRUE,
    0,
    '{
        "collection_type": "products",
        "exclude_title_patterns": ["class", "workshop", "closed"]
    }'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJh1wR5JTgwokRtRdGI6Eryto' OR (c.name = 'Rhino Comedy' AND c.city = 'Suffern' AND c.state = 'NY'))
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'custom'::"ScrapingPlatform"
        AND s.priority = 0
  );

INSERT INTO clubs (
    name, address, website, city, state, zip_code, phone_number,
    latitude, longitude, timezone, country, club_type, google_place_id,
    visible, status
)
SELECT
    'Flop House Comedy Club',
    '362 Grand St, Brooklyn, NY 11211, USA',
    'https://www.flophousecomedy.com/',
    'Brooklyn', 'NY', '11211', '',
    40.7122531, -73.9557515,
    'America/New_York', 'US', 'club',
    'ChIJ06Ugn1JZwokRmkBoiIVB5_M',
    TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJ06Ugn1JZwokRmkBoiIVB5_M'
       OR (name = 'Flop House Comedy Club' AND city = 'Brooklyn' AND state = 'NY')
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'flop_house_json',
    'https://www.flophousecomedy.com/',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJ06Ugn1JZwokRmkBoiIVB5_M' OR (c.name = 'Flop House Comedy Club' AND c.city = 'Brooklyn' AND c.state = 'NY'))
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'custom'::"ScrapingPlatform"
        AND s.priority = 0
  );

INSERT INTO clubs (
    name, address, website, city, state, zip_code, phone_number,
    latitude, longitude, timezone, country, club_type, google_place_id,
    visible, status
)
SELECT
    'The PIT',
    '154 W 29th St, New York, NY 10001, USA',
    'https://thepit-nyc.com/',
    'New York', 'NY', '10001', '',
    40.7473719, -73.9923047,
    'America/New_York', 'US', 'club',
    'ChIJG3e1NKdZwokR26WFFB6Lx7w',
    TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJG3e1NKdZwokR26WFFB6Lx7w'
       OR (name = 'The PIT' AND city = 'New York' AND state = 'NY')
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'json_ld',
    'https://thepit-nyc.com/events/feed/',
    TRUE,
    0,
    '{
        "detail_fetch": {
            "feed_item_links": true,
            "set_same_as_to_detail_url": true,
            "skip_parent_events_with_subevents": true
        }
    }'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJG3e1NKdZwokR26WFFB6Lx7w' OR (c.name = 'The PIT' AND c.city = 'New York' AND c.state = 'NY'))
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'custom'::"ScrapingPlatform"
        AND s.priority = 0
  );

-- Clear false positives from the same high-confidence Places bucket. These are
-- not fixed public comedy venues with venue-owned calendars, so they are kept
-- as hidden non-comedy club rows with no scraping_sources and excluded from
-- future discovery retries via venue_deny_list.
INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT *
FROM (
    VALUES
        ('Raise your dongers', '352 Fox Pointe Dr, Dover, DE 19904, USA', '', 'Dover', 'DE', '19904', 'America/New_York', 'US', 'non_comedy', 'ChIJmTPfAx17x4kR5vWbRtXqdB8', FALSE, 'active'),
        ('Tony''s Crescenzo''s strange humor (podcast on Spotify)', '83 5th St, Frederica, DE 19946, USA', '', 'Frederica', 'DE', '19946', 'America/New_York', 'US', 'non_comedy', 'ChIJ1UPf_OCduIkRFoN2BVfsXzU', FALSE, 'active'),
        ('Comedian Ala Bama', '3905 Dorchester Rd, Gwynn Oak, MD 21207, USA', '', 'Gwynn Oak', 'MD', '21207', 'America/New_York', 'US', 'non_comedy', 'ChIJ58EKNDIbyIkR7QZZSFUaYSM', FALSE, 'active'),
        ('DangItJared', '123 Main St, Berwick, PA 18603, USA', '', 'Berwick', 'PA', '18603', 'America/New_York', 'US', 'non_comedy', 'ChIJ_Ug6nRufxYkRQpLUGjWlUJc', FALSE, 'active'),
        ('The Laff House Atlantic City', '1 Atlantic Ocean, Atlantic City, NJ 08401, USA', 'http://www.thelaffhouseatlanticcity.com/', 'Atlantic City', 'NJ', '08401', 'America/New_York', 'US', 'non_comedy', 'ChIJYU68C-fvwIkRnnT3nK6nICg', FALSE, 'active'),
        ('Funny By The Pound Comedy Cafe', '1156 S Bay Rd, Dover, DE 19901, USA', 'https://www.jreamlandentertainment.com/', 'Dover', 'DE', '19901', 'America/New_York', 'US', 'non_comedy', 'ChIJk1zXo8Rjx4kRP55ii9K1hFc', FALSE, 'active'),
        ('The Looney Bin Comedy Club - Richmond Ave', '921 Richmond Ave, Staten Island, NY 10314, USA', 'http://www.thelooneybincomedyclub.com/', 'Staten Island', 'NY', '10314', 'America/New_York', 'US', 'non_comedy', 'ChIJYf3-4MNNwokR29uqyb4wyL4', FALSE, 'active'),
        ('The Looney Bin Comedy Club - Hylan Blvd', '2001 Hylan Blvd, Staten Island, NY 10306, USA', 'https://thelooneybincomedyclub.com/', 'Staten Island', 'NY', '10306', 'America/New_York', 'US', 'non_comedy', 'ChIJdUNZhZ9MwokRWNxtCHCYniI', FALSE, 'active'),
        ('Chip Ambrogio Comedy', '600 Westwood Ave, River Vale, NJ 07675, USA', 'https://www.chipambrogiocomedy.com/', 'River Vale', 'NJ', '07675', 'America/New_York', 'US', 'non_comedy', 'ChIJHxc11BPvwokRJnO9QrOJfHE', FALSE, 'active'),
        ('Best Comedy Tickets', '128 MacDougal St, New York, NY 10012, USA', 'https://bestcomedytickets.com/', 'New York', 'NY', '10012', 'America/New_York', 'US', 'non_comedy', 'ChIJQXZTgZFZwokRAFmiulJft4w', FALSE, 'active'),
        ('FUNY Stand Up Comedy Classes - The New York Comedy School', 'The Green Room, 201 W 75th St, New York, NY 10023, USA', 'https://funystandup.com/', 'New York', 'NY', '10023', 'America/New_York', 'US', 'non_comedy', 'ChIJD3c4lKVZwokRjdZJoUEQHj8', FALSE, 'active'),
        ('KIDS ''N COMEDY', '208 W 23rd St, New York, NY 10011, USA', 'https://www.kidsncomedy.com/', 'New York', 'NY', '10011', 'America/New_York', 'US', 'non_comedy', 'ChIJC6VawohYwokRSM714XYSVBo', FALSE, 'active'),
        ('The Industry Room', '318 W 53rd St, New York, NY 10019, USA', 'https://www.theindustryroom.com/', 'New York', 'NY', '10019', 'America/New_York', 'US', 'non_comedy', 'ChIJYUSi3gpZwokRkMg8LalEFHY', FALSE, 'active'),
        ('Popped Collar Comedy - Free Show in Bushwick, Brooklyn', '1178 Bushwick Ave, Brooklyn, NY 11221, USA', 'https://www.danwickes.com/popped-collar-comedy-show/', 'Brooklyn', 'NY', '11221', 'America/New_York', 'US', 'non_comedy', 'ChIJ2QNRX-ddwokRj-YibDeFnoM', FALSE, 'active'),
        ('Two in the Bush: A Standup Comedy Showcase', '3569 Broadway, New York, NY 10031, USA', 'https://linktr.ee/twointhebush', 'New York', 'NY', '10031', 'America/New_York', 'US', 'non_comedy', 'ChIJFcAVWzz3wokRw7A5-4bKHNs', FALSE, 'active'),
        ('124 world', '1634 S Bailey St, Philadelphia, PA 19145, USA', '', 'Philadelphia', 'PA', '19145', 'America/New_York', 'US', 'non_comedy', 'ChIJQ-32JULHxokRL-5ZQOzBfMA', FALSE, 'active'),
        ('Case Comedy', '229 S 45th St, Philadelphia, PA 19104, USA', 'https://www.instagram.com/casecomedy/', 'Philadelphia', 'PA', '19104', 'America/New_York', 'US', 'non_comedy', 'ChIJqzj_JPvHxokRSRW9qTzyolw', FALSE, 'active'),
        ('South Jersey Comedy Club at Perkins Center - Collingswood', '30 Irvin Ave, Collingswood, NJ 08108, USA', 'https://comiccure.com/south-jersey-comedy', 'Collingswood', 'NJ', '08108', 'America/New_York', 'US', 'non_comedy', 'ChIJX5NzI7fJxokRn2tAWlZNIto', FALSE, 'active'),
        ('Main Line Laughs at the Palombaro Club', '2632 E County Line Rd, Ardmore, PA 19003, USA', 'https://www.comiccure.com/philly', 'Ardmore', 'PA', '19003', 'America/New_York', 'US', 'non_comedy', 'ChIJETKduEfBxokRPXydhqcDg8w', FALSE, 'active'),
        ('South Jersey Comedy Club at Plays & Players', '957 E Atlantic Ave, Haddonfield, NJ 08033, USA', 'https://comiccure.com/south-jersey-comedy', 'Haddonfield', 'NJ', '08033', 'America/New_York', 'US', 'non_comedy', 'ChIJHYCHtJjNxokRyigUhxrVthE', FALSE, 'active'),
        ('South Jersey Comedy Club at Perkins Center - Moorestown', '395 Kings Hwy, Moorestown, NJ 08057, USA', 'https://comiccure.com/south-jersey-comedy', 'Moorestown', 'NJ', '08057', 'America/New_York', 'US', 'non_comedy', 'ChIJ_wlA6Uw1wYkRLK4iN9LITzE', FALSE, 'active'),
        ('South Jersey Comedy by Comic Cure', '31 West Ave, Pitman, NJ 08071, USA', 'https://comiccure.com/south-jersey-comedy', 'Pitman', 'NJ', '08071', 'America/New_York', 'US', 'non_comedy', 'ChIJpUejQUnXxokRX4eEvKyDLnc', FALSE, 'active'),
        ('New Sight Comedy', '423 Post Oak Ln, Newark, DE 19702, USA', '', 'Newark', 'DE', '19702', 'America/New_York', 'US', 'non_comedy', 'ChIJj9cYtgoHx4kRcIpOJCt_0fA', FALSE, 'active'),
        ('Cool J''s AfterDARK', '1857 Pulaski Hwy, Bear, DE 19701, USA', 'http://www.cooljsafterdark.com/', 'Bear', 'DE', '19701', 'America/New_York', 'US', 'non_comedy', 'ChIJh8PlzpMHx4kRGEDnSClDgw0', FALSE, 'active'),
        ('TravLee Comedy', '627 Smyrna Clayton Blvd, Smyrna, DE 19977, USA', 'https://www.travleecomedy.com/', 'Smyrna', 'DE', '19977', 'America/New_York', 'US', 'non_comedy', 'ChIJMwywGmJxx4kREn69PkTwdaA', FALSE, 'active'),
        ('Poconos Underground Comedy', '622 Main St, Stroudsburg, PA 18360, USA', '', 'Stroudsburg', 'PA', '18360', 'America/New_York', 'US', 'non_comedy', 'ChIJuR4CPQCJxIkRveYIhfPiwt0', FALSE, 'active'),
        ('Comedy Show 3rd Fridays at Fort Hamilton Distillery', '68 34th St Bldg 6, 2nd Floor, Brooklyn, NY 11232, USA', 'https://tallboycomedy.eventbrite.com/', 'Brooklyn', 'NY', '11232', 'America/New_York', 'US', 'non_comedy', 'ChIJTTQXeERbwokRTbAzD7n2iGQ', FALSE, 'active'),
        ('Punching Bag Comedy', '62 Court St, Brooklyn, NY 11201, USA', '', 'Brooklyn', 'NY', '11201', 'America/New_York', 'US', 'non_comedy', 'ChIJfZe5TAtbwokRbgS-m87GIfw', FALSE, 'active'),
        ('Expired Milk Comedy at Planet Showbiz', '274 Morgan Ave Ste 201, Brooklyn, NY 11211, USA', 'https://www.expiredmilkcomedy.com/', 'Brooklyn', 'NY', '11211', 'America/New_York', 'US', 'non_comedy', 'ChIJAQJ5YOJfwokRRcnMweQ58HI', FALSE, 'active'),
        ('Living Room Laughs', '555 Madison Ave 5th floor, New York, NY 10022, USA', 'https://www.livingroomlaughs.com/', 'New York', 'NY', '10022', 'America/New_York', 'US', 'non_comedy', 'ChIJZblXaL5ZwokR-0Uctqy7N0o', FALSE, 'active'),
        ('Comedy Cabaret Comedy Club Northeast', 'At Neighbors Bar, 11580 Roosevelt Blvd, Philadelphia, PA 19116, USA', 'https://www.comedycabaret.com/', 'Philadelphia', 'PA', '19116', 'America/New_York', 'US', 'non_comedy', 'ChIJy5ZWovyyxokRK7e8UIt1DAs', FALSE, 'active'),
        ('The Backroom LIVE', '1206 Mary St, Elizabeth, NJ 07201, USA', 'https://www.eventbrite.com/cc/the-backroom-live-upcoming-shows-4800510', 'Elizabeth', 'NJ', '07201', 'America/New_York', 'US', 'non_comedy', 'ChIJwSKD8ClTwokRirWjcbUWnlU', FALSE, 'active'),
        ('Die Laughing', '943 N Hanover St, Pottstown, PA 19464, USA', 'https://www.dielaughing.org/', 'Pottstown', 'PA', '19464', 'America/New_York', 'US', 'non_comedy', 'ChIJFZh5yjCHxokRz_8cbQHXVRM', FALSE, 'active'),
        ('Kings Highway Comedy', '315 Mill St, Bristol, PA 19007, USA', 'https://kingshighwaycomedy.com/', 'Bristol', 'PA', '19007', 'America/New_York', 'US', 'non_comedy', 'ChIJYXEnsPJNwYkRjESWnP4dY_0', FALSE, 'active'),
        ('Eight Is Never Enough Improv', '318 W 53rd St, New York, NY 10019, USA', 'https://eightimprov.biz/', 'New York', 'NY', '10019', 'America/New_York', 'US', 'non_comedy', 'ChIJucyRblNYwokRBjdPNwuHUZs', FALSE, 'active'),
        ('Laughing Lassi Comedy', '318 W 53rd St, New York, NY 10019, USA', 'https://www.laughinglassi.com/', 'New York', 'NY', '10019', 'America/New_York', 'US', 'non_comedy', 'ChIJu0zwlrtZwokRjqYLUIr_Imk', FALSE, 'active')
) AS denied(name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
WHERE NOT EXISTS (
    SELECT 1 FROM clubs c
    WHERE c.google_place_id = denied.google_place_id
       OR c.name = denied.name
);

INSERT INTO venue_deny_list (
    google_place_id, name, reason, google_primary_type, evidence, added_by, denied_at
)
VALUES
    (
        'ChIJmTPfAx17x4kR5vWbRtXqdB8',
        'Raise your dongers',
        'Google comedy_club candidate has no public website and no evidence of being a fixed comedy venue; name/address look like a non-venue false positive.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "non_venue_false_positive"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJ1UPf_OCduIkRFoN2BVfsXzU',
        'Tony''s Crescenzo''s strange humor (podcast on Spotify)',
        'Google record describes a podcast/personality, not a fixed comedy venue with a public event calendar.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "podcast_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJ58EKNDIbyIkR7QZZSFUaYSM',
        'Comedian Ala Bama',
        'Individual comedian listing, not a fixed comedy venue.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "person_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJ_Ug6nRufxYkRQpLUGjWlUJc',
        'DangItJared',
        'Individual performer/brand listing, not a fixed comedy venue.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "person_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJYU68C-fvwIkRnnT3nK6nICg',
        'The Laff House Atlantic City',
        'Discovered website no longer resolves, and no venue-owned public calendar could be verified for this Atlantic City Places record.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "stale_site_no_calendar"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJk1zXo8Rjx4kRP55ii9K1hFc',
        'Funny By The Pound Comedy Cafe',
        'Google comedy_club candidate points to a Wix site that returns 404 and exposes no public venue calendar or fixed comedy-club event surface.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "non_venue_or_stale_business_false_positive"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJYf3-4MNNwokR29uqyb4wyL4',
        'The Looney Bin Comedy Club',
        'Website returns an error page and exposes no public venue calendar; not safe to onboard as an active scrape target.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "stale_site_no_calendar"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJdUNZhZ9MwokRWNxtCHCYniI',
        'The Looney Bin Comedy Club',
        'Alternate Google record for the same stale Looney Bin Staten Island brand; website returns 404/error and exposes no public venue calendar.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "stale_site_no_calendar"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJHxc11BPvwokRJnO9QrOJfHE',
        'Chip Ambrogio Comedy',
        'Individual comedian website/listing, not a fixed comedy venue.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "person_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJQXZTgZFZwokRAFmiulJft4w',
        'Best Comedy Tickets',
        'Ticket reseller/listing site for multiple NYC comedy venues, not a fixed venue-owned comedy club calendar to onboard as a club.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "ticket_reseller_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJD3c4lKVZwokRjdZJoUEQHj8',
        'FUNY Stand Up Comedy Classes - The New York Comedy School',
        'Comedy class/school program at a rented room, not a fixed comedy venue calendar to onboard as a club.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "classes_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJC6VawohYwokRSM714XYSVBo',
        'KIDS ''N COMEDY',
        'Youth comedy program/show listing that links to Gotham Comedy Club events; not a distinct fixed venue calendar.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "program_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJYUSi3gpZwokRkMg8LalEFHY',
        'The Industry Room',
        'Comedy class/training-room listing; public ticket signal found was a stand-up class, not a fixed public club calendar.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "classes_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJ2QNRX-ddwokRj-YibDeFnoM',
        'Popped Collar Comedy - Free Show in Bushwick, Brooklyn',
        'Named recurring/showcase listing at another venue, not a distinct fixed comedy club.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "showcase_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJFcAVWzz3wokRw7A5-4bKHNs',
        'Two in the Bush: A Standup Comedy Showcase',
        'Named stand-up showcase listing, not a distinct fixed comedy venue.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "showcase_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJQ-32JULHxokRL-5ZQOzBfMA',
        '124 world',
        'Google comedy_club candidate has no website and no verified public venue-owned calendar; address appears to be a non-public/private listing.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "non_venue_false_positive"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJqzj_JPvHxokRSRW9qTzyolw',
        'Case Comedy',
        'Instagram-only comedy show/producer listing, not a fixed venue-owned comedy-club calendar.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "producer_or_showcase_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJX5NzI7fJxokRn2tAWlZNIto',
        'South Jersey Comedy Club at Perkins Center',
        'Comic Cure/South Jersey Comedy recurring producer listing at a host venue, not a distinct fixed comedy club.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "producer_or_showcase_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJETKduEfBxokRPXydhqcDg8w',
        'Main Line Laughs at the Palombaro Club',
        'Comic Cure/Main Line Laughs recurring producer listing at a host venue, not a distinct fixed comedy club.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "producer_or_showcase_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJHYCHtJjNxokRyigUhxrVthE',
        'South Jersey Comedy Club at Plays & Players',
        'Comic Cure/South Jersey Comedy recurring producer listing at a host venue, not a distinct fixed comedy club.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "producer_or_showcase_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJ_wlA6Uw1wYkRLK4iN9LITzE',
        'South Jersey Comedy Club at Perkins Center',
        'Comic Cure/South Jersey Comedy recurring producer listing at a host venue, not a distinct fixed comedy club.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "producer_or_showcase_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJpUejQUnXxokRX4eEvKyDLnc',
        'South Jersey Comedy by Comic Cure',
        'Comic Cure/South Jersey Comedy producer listing, not a distinct fixed comedy club.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "producer_or_showcase_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJj9cYtgoHx4kRcIpOJCt_0fA',
        'New Sight Comedy',
        'Google comedy_club candidate has no website and no verified public venue-owned calendar; address appears to be a non-public/private listing.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "non_venue_false_positive"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJh8PlzpMHx4kRGEDnSClDgw0',
        'Cool J''s AfterDARK',
        'Comedy producer/event-series listing rather than a fixed venue-owned comedy-club calendar.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "producer_or_showcase_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJMwywGmJxx4kREn69PkTwdaA',
        'TravLee Comedy',
        'Individual/producer comedy-brand listing, not a fixed comedy venue.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "producer_or_person_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJuR4CPQCJxIkRveYIhfPiwt0',
        'Poconos Underground Comedy',
        'Named comedy producer/showcase listing with no venue-owned public calendar, not a distinct fixed comedy club.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "producer_or_showcase_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJTTQXeERbwokRTbAzD7n2iGQ',
        'Comedy Show 3rd Fridays of the month at Fort Hamilton Distillery',
        'Named monthly stand-up showcase at Fort Hamilton Distillery, not a distinct fixed comedy club.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "showcase_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJfZe5TAtbwokRbgS-m87GIfw',
        'Punching Bag Comedy',
        'Named comedy show/producer listing without a venue-owned public calendar, not a distinct fixed comedy club.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "producer_or_showcase_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJAQJ5YOJfwokRRcnMweQ58HI',
        'Expired Milk Comedy (at Planet Showbiz)',
        'Named show/producer listing at another venue, not a distinct fixed comedy club.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "showcase_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJZblXaL5ZwokR-0Uctqy7N0o',
        'Living Room Laughs',
        'Private-show producer listing at an office address; site offers private comedy show packages rather than a fixed public venue-owned calendar.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "private_show_producer_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJy5ZWovyyxokRK7e8UIt1DAs',
        'Comedy Cabaret Comedy Club Northeast',
        'Closed Northeast Philadelphia Comedy Cabaret location; venue page says the Northeast club is closed due to building issues.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "closed_location"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJwSKD8ClTwokRirWjcbUWnlU',
        'The Backroom LIVE',
        'Eventbrite collection/organizer listing for Janmichael Conde rather than a fixed venue-owned comedy-club calendar; standalone domain timed out and organizer feed returned no shows through the existing Eventbrite scraper.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "producer_or_eventbrite_collection_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJFZh5yjCHxokRz_8cbQHXVRM',
        'Die Laughing',
        'Splash-page listing with no public venue-owned calendar; /events, /calendar, and /shows all return 404, so there is no safe source to onboard as a fixed comedy club.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "no_public_calendar_false_positive"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJYXEnsPJNwYkRjESWnP4dY_0',
        'Kings Highway Comedy',
        'GoDaddy site says Up Coming Shows Coming Soon and exposes no public ticket or calendar endpoint; /shows, /events, and /calendar return 404.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "no_public_calendar_false_positive"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJucyRblNYwokRBjdPNwuHUZs',
        'Eight Is Never Enough Improv',
        'Improv/class/showcase brand at a shared class/performance address, not a distinct venue-owned comedy-club calendar.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "classes_or_showcase_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    ),
    (
        'ChIJu0zwlrtZwokRjqYLUIr_Imk',
        'Laughing Lassi Comedy',
        'Named comedy show/producer listing at a shared class/performance address, not a distinct fixed comedy club.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "producer_or_showcase_not_venue"}'::jsonb,
        'TASK-3563',
        NOW()
    )
ON CONFLICT (google_place_id) DO NOTHING;
