-- Onboard Martinez Campbell Theater (Martinez, CA) via the existing eventbrite scraper - TASK-3191.
--
-- The Campbell Theater (a Wix site) hosts the Contra Costa Comedy / "CoCoComedy"
-- stand-up series ("Comedy at the Campbell"), ticketed through the Contra Costa
-- Comedy Eventbrite organizer (10954147007). This wires to the generic `eventbrite`
-- scraper in organizer mode: it groups the organizer's events by Eventbrite venue
-- and attaches each show to the matching per-venue club. The organizer's
-- "Martinez Campbell Theater" venue name matches this club exactly, so its
-- Comedy-at-the-Campbell shows attach here (no code needed). If CoCoComedy adds
-- shows at other venues (e.g. the Martinez amphitheater "Comedy Under the Stars"),
-- the scraper auto-creates those per-venue clubs from the same feed.
--
-- NOTE (verified 2026-06-23): a real scrape of the organizer feed produced 2
-- upcoming comedy shows, all matched to this club ("reused existing Eventbrite
-- venue club 'Martinez Campbell Theater'").

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Martinez Campbell Theater', '636 Ward St, Martinez, CA 94553, USA',
    'https://www.campbelltheater.com/',
    'Martinez', 'CA', '94553', 'America/Los_Angeles', 'US', 'club',
    'ChIJP6USGIRvhYARFSYPM6BOYq0', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJP6USGIRvhYARFSYPM6BOYq0'
       OR name = 'Martinez Campbell Theater'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com/o/contra-costa-comedy-10954147007',
    '10954147007',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJP6USGIRvhYARFSYPM6BOYq0' OR c.name = 'Martinez Campbell Theater')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite'
  );
