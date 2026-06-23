-- Onboard The Spotlight Comedy (Secret Comedy Show) via the Eventbrite organizer scraper - TASK-3178.
--
-- The Spotlight Comedy is a roving comedy producer: it runs the weekly "Secret
-- Comedy Show" stand-up at Mr. Mahjong's (San Francisco) plus an occasional
-- "Comedy Claremont" night at El Ranchero (Claremont, CA). Its own Squarespace
-- site (thespotlightcomedy.com/sanfrancisco) sells tickets through Eventbrite,
-- under organizer "The Spotlight Comedy" (id 62788201173).
--
-- Because the producer plays at varying venues, it is modeled as a HIDDEN proxy
-- club (visible = FALSE) wired to the Eventbrite scraper in ORGANIZER mode (the
-- source_url contains "/o/"). The scraper groups the organizer feed by venue and
-- upserts a per-venue club for each (Mr. Mahjong's, El Ranchero); the actual
-- shows surface under those per-venue clubs, not under this proxy. This mirrors
-- existing producer proxies (Snowflake Comedy, Henceforth Comedy, Puff Puff Laugh).
--
-- NOTE (verified 2026-06-23): a real scrape fetched 250 live events (all stand-up)
-- and persisted 158 shows within the global 18-month future cap -- 156 at the
-- auto-created Mr. Mahjong's club and 2 at El Ranchero. The far-future weekly
-- recurrences beyond 18 months are intentionally trimmed by show-date validation.
-- The auto-created per-venue clubs are produced by the scraper at runtime and are
-- intentionally NOT inserted here -- only the proxy club + its scraping_sources row
-- are reproducible data.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'The Spotlight Comedy', '260 Kearny St, San Francisco, CA 94104, USA',
    'https://www.thespotlightcomedy.com/sanfrancisco',
    'San Francisco', 'CA', '94104', 'America/Los_Angeles', 'US', 'club',
    'ChIJpW131CqBhYARCNC36Zr5LAk', FALSE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJpW131CqBhYARCNC36Zr5LAk'
       OR name = 'The Spotlight Comedy'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com/o/the-spotlight-comedy-62788201173',
    '62788201173',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJpW131CqBhYARCNC36Zr5LAk' OR c.name = 'The Spotlight Comedy')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite'
  );
