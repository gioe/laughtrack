-- TASK-2864: Onboard Canton Comedy Boom (Canton, OH) — Eventbrite organizer.
--
-- Discovered via the discover-comedy-venues skill (objective #2, near ZIP 44622).
-- Canton Comedy Boom is an Eventbrite *organizer* (id 74842555093) producing
-- recurring stand-up shows; the existing `eventbrite` scraper handles organizer
-- mode by detecting the /o/ source_url. This adds the visible anchor club and
-- its scraping source. Both inserts are idempotent (guarded by NOT EXISTS) so
-- this is a no-op on environments where the rows were already created manually
-- (prod) while still reproducing the state on a fresh database.

INSERT INTO clubs (
    name, address, website, city, state, zip_code, timezone, country,
    club_type, google_place_id, visible, status
)
SELECT
    'Canton Comedy Boom',
    '324 Cleveland Ave NW, Canton, OH 44702',
    'https://cantoncomedyboom.com/',
    'Canton', 'OH', '44702', 'America/New_York', 'US',
    'club', 'ChIJGYwxqh_RNogRj9s0QgAPqkA', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs WHERE name = 'Canton Comedy Boom'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    priority, enabled, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com/o/74842555093',
    '74842555093',
    0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c
WHERE c.name = 'Canton Comedy Boom'
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite'
  );
