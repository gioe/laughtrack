-- Onboard two more Boston-cluster comedy venues discovered via
-- discover-comedy-venues near ZIP 02101 - TASK-3151 (fourth batch).
--
-- 8. Kismet Improv (1005 Main St Ste 2205, Pawtucket, RI 02860) — dedicated
--    improv/standup club on Wix. Wired via the wix_events scraper (Wix Events app
--    component comp-l65a04m5); all-comedy, no filter needed. Verified 2026-06-21:
--    a real scrape persisted 27 shows for club 10952.
--
-- 9. Providence Comedy Underground (121 Washington St, Providence, RI 02903) —
--    dedicated comedy producer running every Fri/Sat at The George / Hide
--    Speakeasy. Tickets via the Eventbrite organizer "providencecomedyunderground"
--    (id 31203223233); single-venue, all-comedy. Verified 2026-06-21: a real scrape
--    persisted 226 shows for club 10953.

-- ---- Kismet Improv (Wix Events) ----
INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Kismet Improv', '1005 Main St Ste 2205', 'http://www.kismetimprov.com/',
    'Pawtucket', 'RI', '02860', 'America/New_York', 'US', 'club',
    'ChIJ2WVxU6lF5IkR2DfH18x--Iw', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJ2WVxU6lF5IkR2DfH18x--Iw'
       OR name = 'Kismet Improv'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, wix_event_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'wix_events'::"ScrapingPlatform",
    'wix_events',
    'https://www.kismetimprov.com',
    'comp-l65a04m5',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJ2WVxU6lF5IkR2DfH18x--Iw' OR c.name = 'Kismet Improv')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'wix_events'
  );

-- ---- Providence Comedy Underground (Eventbrite) ----
INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Providence Comedy Underground', '121 Washington St', 'https://www.providencecomedyunderground.com/',
    'Providence', 'RI', '02903', 'America/New_York', 'US', 'club',
    'ChIJoWc1Ww1F5IkRoBRKIEeqDOU', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJoWc1Ww1F5IkRoBRKIEeqDOU'
       OR name = 'Providence Comedy Underground'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com/o/31203223233',
    '31203223233',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJoWc1Ww1F5IkRoBRKIEeqDOU' OR c.name = 'Providence Comedy Underground')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite'
  );
