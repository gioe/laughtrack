-- Onboard three more Boston-cluster comedy venues discovered via
-- discover-comedy-venues near ZIP 02101 - TASK-3151 (third batch).
--
-- 5. The Brook (319 New Zealand Rd, Seabrook, NH 03874) — casino with the Seasons
--    Showroom booking touring comedians. Site is a Galaxy.tf CMS that emits clean
--    schema.org Event JSON-LD on /promotions_and_events/<slug> detail pages. Wired
--    via the generic json_ld scraper in detail-fetch mode (url_path_prefix) with
--    comedy_filter ON (mixed-use venue: comedy + music + dining promos). Verified
--    2026-06-21: a real scrape persisted 1 comedy show (Joe List, 2026-09-18) for
--    club 10948. NOTE: Phil Hanley (2026-08-14) is currently dropped because his
--    blurb says "night of laughs" without a literal comedy keyword — tracked in
--    TASK-3159 (broaden is_comedy_event); this venue will under-report until then.
--
-- 6. Lots of Laughs Comedy Lounge (1120 Osgood St / Joe Fish, North Andover, MA
--    01845) — Johnny Pizzi's single-venue comedy series. Tickets via the Eventbrite
--    organizer "Lots of Laughs Productions" (id 19238583950). Wired but 0 upcoming
--    at onboard time (organizer publishes in batches); will populate on the nightly
--    once they post shows. Not a failure — the organizer id is correct/single-venue.
--
-- 7. Bobby's Place Night Club (60 Weir St, Taunton, MA 02780) — venue-owned
--    Eventbrite organizer "Bobby's Night Club" (id 113163289571), comedy-only feed.
--    Wired but 0 upcoming at onboard time (only one historical comedy showcase on
--    record); future-proofed for when the recurring showcase resumes.

-- ---- The Brook (json_ld detail-fetch + comedy_filter) ----
INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'The Brook', '319 New Zealand Rd', 'http://livefreeandplay.com/',
    'Seabrook', 'NH', '03874', 'America/New_York', 'US', 'club',
    'ChIJgdxZaH7m4okRkJF5cG2OyGQ', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJgdxZaH7m4okRkJF5cG2OyGQ'
       OR name = 'The Brook'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'json_ld',
    'https://livefreeandplay.com/promotions_and_events',
    TRUE,
    0,
    '{"detail_fetch":{"url_path_prefix":"/promotions_and_events/"},"comedy_filter":true}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJgdxZaH7m4okRkJF5cG2OyGQ' OR c.name = 'The Brook')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'json_ld'
  );

-- ---- Lots of Laughs Comedy Lounge (Eventbrite) ----
INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Lots of Laughs Comedy Lounge', '1120 Osgood St', 'https://www.eventbrite.com/o/19238583950',
    'North Andover', 'MA', '01845', 'America/New_York', 'US', 'club',
    'ChIJMWOlcI0G44kRjzzvFYioUrY', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJMWOlcI0G44kRjzzvFYioUrY'
       OR name = 'Lots of Laughs Comedy Lounge'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com/o/19238583950',
    '19238583950',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJMWOlcI0G44kRjzzvFYioUrY' OR c.name = 'Lots of Laughs Comedy Lounge')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite'
  );

-- ---- Bobby's Place Night Club (Eventbrite) ----
INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Bobby''s Place Night Club', '60 Weir St', 'https://www.bobbysplacenightclub.com/',
    'Taunton', 'MA', '02780', 'America/New_York', 'US', 'club',
    'ChIJRepkPQCN5IkRkR-CsXHSEZQ', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJRepkPQCN5IkRkR-CsXHSEZQ'
       OR name = 'Bobby''s Place Night Club'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com/o/113163289571',
    '113163289571',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJRepkPQCN5IkRkR-CsXHSEZQ' OR c.name = 'Bobby''s Place Night Club')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite'
  );
