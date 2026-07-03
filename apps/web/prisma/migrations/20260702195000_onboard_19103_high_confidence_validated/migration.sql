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
--
-- After this migration is deployed, run:
--   cd apps/scraper && make scrape-club CLUB='The N Crowd'
--   cd apps/scraper && make scrape-club CLUB='Laughing Stock Comedy Club'
--   cd apps/scraper && make scrape-club CLUB='Brooklyn Comedy Collective'
--   cd apps/scraper && make scrape-club CLUB='Meadowlands Comedy Club'
--   cd apps/scraper && make scrape-club CLUB='High Line Comedy Club'
--   cd apps/scraper && make scrape-club CLUB='BATSU!'

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
        ('Chip Ambrogio Comedy', '600 Westwood Ave, River Vale, NJ 07675, USA', 'https://www.chipambrogiocomedy.com/', 'River Vale', 'NJ', '07675', 'America/New_York', 'US', 'non_comedy', 'ChIJHxc11BPvwokRJnO9QrOJfHE', FALSE, 'active'),
        ('FUNY Stand Up Comedy Classes - The New York Comedy School', 'The Green Room, 201 W 75th St, New York, NY 10023, USA', 'https://funystandup.com/', 'New York', 'NY', '10023', 'America/New_York', 'US', 'non_comedy', 'ChIJD3c4lKVZwokRjdZJoUEQHj8', FALSE, 'active'),
        ('Popped Collar Comedy - Free Show in Bushwick, Brooklyn', '1178 Bushwick Ave, Brooklyn, NY 11221, USA', 'https://www.danwickes.com/popped-collar-comedy-show/', 'Brooklyn', 'NY', '11221', 'America/New_York', 'US', 'non_comedy', 'ChIJ2QNRX-ddwokRj-YibDeFnoM', FALSE, 'active'),
        ('Two in the Bush: A Standup Comedy Showcase', '3569 Broadway, New York, NY 10031, USA', 'https://linktr.ee/twointhebush', 'New York', 'NY', '10031', 'America/New_York', 'US', 'non_comedy', 'ChIJFcAVWzz3wokRw7A5-4bKHNs', FALSE, 'active')
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
        'ChIJHxc11BPvwokRJnO9QrOJfHE',
        'Chip Ambrogio Comedy',
        'Individual comedian website/listing, not a fixed comedy venue.',
        'comedy_club',
        '{"task": "TASK-3563", "discovery": "19103 high-confidence Google Places bucket", "classification": "person_not_venue"}'::jsonb,
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
    )
ON CONFLICT (google_place_id) DO NOTHING;
