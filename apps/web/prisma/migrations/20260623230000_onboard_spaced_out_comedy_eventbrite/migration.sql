-- Onboard Spaced Out Comedy (San Jose, CA) via the generic Eventbrite scraper - TASK-3228.
--
-- CONTEXT: Spaced Out ("San Jose's #1 Indie Comedy Show", https://spacedoutcomedy.com/)
-- is a recurring monthly stand-up comedy series that pops up inside Mystérieux Brand,
-- a barbershop/apparel store at 28 N Almaden Ave #30 in downtown San Jose's San Pedro
-- Square. The series self-publishes its dated, ticketed shows through its own Eventbrite
-- organizer "Spaced Out Comedy" (https://www.eventbrite.com/o/spaced-out-comedy-80647104493).
--
-- PLATFORM / MODE: Eventbrite, generic `eventbrite` scraper. The organizer feed
-- (organizer 80647104493) tags every event with the Eventbrite VENUE "Mystérieux Brand"
-- (venue id 298215115). Because that venue name differs from this club's name ("Spaced
-- Out Comedy"), organizer mode's strict name+location match would mint a duplicate
-- "Mystérieux Brand" auto-club and split shows (see eventbrite onboarding convention,
-- TASK-3151 caveat). This is a SINGLE fixed physical venue, so we wire SINGLE-VENUE mode
-- instead: source_url='https://www.eventbrite.com' (no /o/ segment) + eventbrite_id =
-- the Eventbrite venue id 298215115. The API token OWNS venue 298215115, so the
-- /venues/{id}/events/ endpoint returns the feed directly (verified below) and every
-- show is forced onto this one club. visible = TRUE (fixed venue, its own identity).
--
-- The feed is pure comedy (single stand-up series), so no comedy title filter is needed.
--
-- VERIFICATION (2026-06-23): a real scrape of venue 298215115 via the eventbrite scraper
-- returned the live event "Spaced Out: Standup Comedy in Downtown San Jose" (2026-07-25),
-- and `make scrape-club-id` persisted it (1 show). Future monthly shows attach
-- automatically on each nightly run.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Spaced Out Comedy',
    '28 N Almaden Ave #30, San Jose, CA 95110, USA',
    'https://spacedoutcomedy.com/',
    'San Jose',
    'CA',
    '95110',
    'America/Los_Angeles',
    'US',
    'club',
    'ChIJ08q2uW7Nj4ARhRQpV2EzRvY',
    TRUE,
    'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJ08q2uW7Nj4ARhRQpV2EzRvY'
       OR lower(name) = lower('Spaced Out Comedy')
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
    '298215115',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE c.google_place_id = 'ChIJ08q2uW7Nj4ARhRQpV2EzRvY'
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'eventbrite'::"ScrapingPlatform"
        AND s.priority = 0
  )
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.eventbrite_id = '298215115'
  );
