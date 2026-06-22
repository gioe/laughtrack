-- Onboard Playhouse on Park (West Hartford, CT) via the new tix_com scraper - TASK-3172.
--
-- Playhouse on Park runs a recurring "Comedy Nights" series among its
-- musical/theatre season, ticketed through Tix.com (org 2704). The new tix_com
-- scraper reads the anonymous JSON feed
-- (api_ots/onlinesales/events/organization/2704) and the source opts into comedy
-- isolation via metadata.comedy_filter so the musicals/plays don't surface.
--
-- NOTE (verified 2026-06-22): a real scrape runs cleanly and extracts the full
-- 45-event feed, but the comedy_filter currently keeps 0 because Season 17's
-- Comedy Nights ended May 2026 and Season 18 comedy is not yet on sale. The row
-- will auto-populate when the next comedy season is listed (the tix_com smoke
-- test exercises the comedy keep-path with a fixture comedy production).

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Playhouse on Park', '244 Park Rd', 'http://www.playhouseonpark.org/',
    'West Hartford', 'CT', '06119', 'America/New_York', 'US', 'club',
    'ChIJWyyD8sas54kRCZJwgbAA50A', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJWyyD8sas54kRCZJwgbAA50A'
       OR name = 'Playhouse on Park'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'tix_com',
    'https://www.tix.com/ticket-sales/playhouseonpark/2704',
    TRUE,
    0,
    jsonb_build_object('comedy_filter', true),
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJWyyD8sas54kRCZJwgbAA50A' OR c.name = 'Playhouse on Park')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'tix_com'
  );
