-- Onboard Visani (Port Charlotte, FL) via its ThunderTix storefront.
--
-- Venue site: https://www.visani.net/
-- Calendar/tickets: https://visanientertainmentinc.thundertix.com/events?display=calendar
--
-- The ThunderTix calendar includes comedy plus tribute/music/special appearance
-- programming. The generic ThunderTix scraper supports metadata title-prefix
-- skips, so this source excludes the non-comedy titles observed in the current
-- 12-week API window while keeping the comedy/headliner events.

INSERT INTO clubs (
  name, address, website, city, state, zip_code, timezone, country,
  club_type, visible, status
)
SELECT
  'Visani',
  '2400 Kings Highway, Port Charlotte, FL 33980',
  'https://www.visani.net/',
  'Port Charlotte',
  'FL',
  '33980',
  'America/New_York',
  'US',
  'club',
  true,
  'active'
WHERE NOT EXISTS (
  SELECT 1
  FROM clubs
  WHERE website = 'https://www.visani.net/'
     OR lower(name) = 'visani'
);

INSERT INTO scraping_sources (
  club_id, platform, scraper_key, source_url, priority, enabled, metadata
)
SELECT
  c.id,
  'thundertix'::"ScrapingPlatform",
  'thundertix',
  'https://visanientertainmentinc.thundertix.com',
  0,
  true,
  jsonb_build_object(
    'title_skip_prefixes',
    'Dwight Icenhower and The Blue Suede Review,General Hospital''s Maurice Benard,Majesty of Rock - The Ultimate Tribute to Journey,Classic Rock Legends,Billy & Elton: Double Bill'
  )
FROM clubs c
WHERE c.name = 'Visani'
  AND c.website = 'https://www.visani.net/'
  AND NOT EXISTS (
    SELECT 1
    FROM scraping_sources ss
    WHERE ss.club_id = c.id
      AND ss.scraper_key = 'thundertix'
      AND ss.source_url = 'https://visanientertainmentinc.thundertix.com'
  );
