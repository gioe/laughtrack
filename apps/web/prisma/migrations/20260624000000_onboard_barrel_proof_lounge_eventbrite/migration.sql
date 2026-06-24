-- Onboard Barrel Proof Lounge (Santa Rosa, CA) via the existing eventbrite scraper - TASK-3197.
--
-- Barrel Proof Lounge is a mixed-use bar at 501 Mendocino Ave, Santa Rosa. Its own
-- WordPress site (barrelprooflounge.com) embeds the Eventbrite API plugin and links
-- every event out to Eventbrite under a single organizer, "Barrel Proof Lounge"
-- (52973374973). That ONE feed is mixed-use: karaoke ("Big Stage Karaoke Wednesdays",
-- "Karaoke Sundays"), live music ("Live Music Happy Hour ...", "The Honeycomb Hideout
-- Live Music"), and the venue's recurring comedy:
--   - "Sunday Evening Comedy (FREE)"
--   - "Tuesday Night Comedy Showcase with Tony Sparks"
--   - "Wednesday Night Comedy Open Mic"
-- Because the music/karaoke titles are unpredictable, an exclude list can't isolate
-- the comedy, so the source carries an `include_title_patterns` comedy allowlist
-- (TASK-3205 added include semantics to the eventbrite scraper): the scraper keeps
-- ONLY events whose title matches comedy / stand-up / comedian and drops the rest.
-- Every comedy title above contains "Comedy", so the allowlist catches all three.
--
-- Organizer mode: the eventbrite scraper groups the organizer's (comedy) events by
-- Eventbrite venue and attaches each show to the matching per-venue club. The
-- Eventbrite API venue name "Barrel Proof Lounge" (Santa Rosa, CA; EB venue id
-- 295829140) matches this club, so the filtered comedy shows attach here.
--
-- NOTE (verified 2026-06-24): the organizer feed scrapes cleanly (HTTP 200), and the
-- comedy include-filter keeps only the three recurring comedy series. If no comedy
-- event is currently on sale, shows populate via the venue-name match the next time a
-- comedy event is listed (same timing-gap pattern as TASK-3205 / Deja Blue).

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Barrel Proof Lounge', '501 Mendocino Ave, Santa Rosa, CA 95401',
    'http://www.barrelprooflounge.com/',
    'Santa Rosa', 'CA', '95401', 'America/Los_Angeles', 'US', 'club',
    'ChIJ8Rv0bqlHhIARkNvPaLl-eeA', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJ8Rv0bqlHhIARkNvPaLl-eeA'
       OR name = 'Barrel Proof Lounge'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com/o/barrel-proof-lounge-52973374973',
    '52973374973',
    TRUE,
    0,
    '{"include_title_patterns": ["comedy", "stand[ -]?up", "comedian"]}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJ8Rv0bqlHhIARkNvPaLl-eeA' OR c.name = 'Barrel Proof Lounge')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite'
  );
