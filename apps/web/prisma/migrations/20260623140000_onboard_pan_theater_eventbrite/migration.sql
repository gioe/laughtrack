-- Onboard Pan Theater (Oakland, CA) via the existing eventbrite scraper - TASK-3183.
--
-- Pan Theater is Oakland's improv comedy theater (120 Frank H. Ogawa Plaza). Its
-- own site (pantheater.com, a static Sitely build) lists shows only as free-text
-- prose with no structured dates, but it sells tickets through its Eventbrite
-- organizer (pan-theater-2363477336) — "tickets via Eventbrite or $20 cash at the
-- door". The Eventbrite organizer feed is the structured datasource, so this wires
-- to the generic `eventbrite` scraper (organizer id 2363477336) — no code needed.
--
-- NOTE (verified 2026-06-23): a real scrape of the organizer feed extracts and
-- persists 8 upcoming improv comedy shows.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Pan Theater', '120 Frank H. Ogawa Plaza, Oakland, CA 94612, USA',
    'https://www.pantheater.com/',
    'Oakland', 'CA', '94612', 'America/Los_Angeles', 'US', 'club',
    'ChIJXb0yEq2Aj4ARPPOQ0WTVEm0', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJXb0yEq2Aj4ARPPOQ0WTVEm0'
       OR name = 'Pan Theater'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com/o/pan-theater-2363477336',
    '2363477336',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJXb0yEq2Aj4ARPPOQ0WTVEm0' OR c.name = 'Pan Theater')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite'
  );
