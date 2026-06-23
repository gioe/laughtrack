-- Onboard Haus of Comedy (Sacramento, CA) via the existing crowdwork scraper - TASK-3200.
--
-- Haus of Comedy (Windhaus Improv) is a fixed improv/stand-up comedy venue at the
-- Eagle Theater, 921 Front St, Sacramento. Its Squarespace site sells tickets through
-- CrowdWork (theatre slug "windhausimprov"); the show listings are hydrated from the
-- CrowdWork v2 API: https://crowdwork.com/api/v2/windhausimprov/shows (10 recurring
-- shows -> 64 dated performances at onboarding, including the "Valley Heat" stand-up
-- showcase). This wires the venue to the generic `crowdwork` scraper, which reads the
-- API URL from scraping_sources.source_url and its config from metadata.
--
-- The CrowdWork API returns Rails-style timezone names ("Pacific Time (US & Canada)"),
-- so metadata sets rails_to_iana=true to normalise them to IANA, with
-- default_timezone=America/Los_Angeles as the fallback. Verified 2026-06-23:
-- `make scrape-club-id ID=<id>` -> "Scraped 64 shows for Haus of Comedy" (7pm Pacific
-- show stored as 02:00 UTC = correct).
--
-- Haus of Comedy is its own fixed venue -> visible=TRUE.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Haus of Comedy',
    'Eagle Theater, 921 Front St, Sacramento, CA 95814, USA',
    'https://hausofcomedy.com/',
    'Sacramento', 'CA', '95814', 'America/Los_Angeles', 'US', 'club',
    'ChIJF9AoTLyMwEwRTvdQJw7z_w8', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJF9AoTLyMwEwRTvdQJw7z_w8'
       OR name = 'Haus of Comedy'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'crowdwork'::"ScrapingPlatform",
    'crowdwork',
    'https://crowdwork.com/api/v2/windhausimprov/shows',
    TRUE,
    0,
    '{"rails_to_iana": true, "default_timezone": "America/Los_Angeles"}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJF9AoTLyMwEwRTvdQJw7z_w8' OR c.name = 'Haus of Comedy')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'crowdwork'
  );
