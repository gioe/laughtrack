-- Onboard Deja Blue (Seaside, CA) via the existing eventbrite scraper - TASK-3205.
--
-- Deja Blue is a soul-food restaurant + "Blues, Jazz & Comedy Club" at 500 Broadway
-- Ave, Seaside. Its own site (dejabluelive.com) links every event out to Eventbrite
-- under a single organizer, Daryll Choates (34313519965). That ONE feed is mixed-use:
-- music acts named after the band/DJ (e.g. "Aki Kumar", "DJ Carmaa", "Isaiah Band")
-- alongside the venue's recurring comedy ("Summer Heat Comedy Show", "Live at Deja
-- Blue: Comedy All Stars"). Because the music titles are unpredictable, an exclude
-- list can't isolate the comedy, so the source carries an `include_title_patterns`
-- comedy allowlist (TASK-3205 added include semantics to the eventbrite scraper):
-- the scraper keeps ONLY events whose title matches comedy / stand-up / comedian and
-- drops the music.
--
-- Organizer mode: the eventbrite scraper groups the organizer's (comedy) events by
-- Eventbrite venue and attaches each show to the matching per-venue club. The
-- Eventbrite API venue name "Deja Blue" (Seaside, CA) matches this club, so the
-- comedy shows attach here.
--
-- NOTE (verified 2026-06-23): the organizer feed scrapes cleanly (HTTP 200, 3 upcoming
-- events), and the comedy include-filter correctly drops all 3 (all currently-listed
-- events are music) -> 0 shows right now. Deja Blue's comedy is recurring but sparse
-- (Jul 2025 "Comedy All Stars", May 2026 "Summer Heat Comedy Show"), and no comedy is
-- on sale at this moment. Shows populate via the venue-name match the next time a
-- comedy event is listed (same timing-gap pattern as TASK-3192 / Clayton Club).

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Deja Blue', '500 Broadway Ave, Seaside, CA 93955',
    'http://www.dejabluelive.com/',
    'Seaside', 'CA', '93955', 'America/Los_Angeles', 'US', 'club',
    'ChIJ40x9RnfljYARPIXV1Fht1AU', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJ40x9RnfljYARPIXV1Fht1AU'
       OR name = 'Deja Blue'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com/o/daryll-choates-34313519965',
    '34313519965',
    TRUE,
    0,
    '{"include_title_patterns": ["comedy", "stand[ -]?up", "comedian"]}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJ40x9RnfljYARPIXV1Fht1AU' OR c.name = 'Deja Blue')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite'
  );
