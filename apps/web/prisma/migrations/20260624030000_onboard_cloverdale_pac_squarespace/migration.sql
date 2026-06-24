-- Onboard Cloverdale Performing Arts Center (Cloverdale, CA) via the generic squarespace scraper - TASK-3236.
--
-- Cloverdale PAC (cloverdaleperformingarts.com) is a mixed-use community
-- performing-arts center whose show calendar is a Squarespace Events collection
-- (GET /api/open/GetItemsByMonth?collectionId=66ddfcba655ffa05a0699e3e). SimpleTix
-- appears only as the per-event buy-link clickthrough; the venue's OWN Squarespace
-- calendar is the datasource. The collection mixes the occasional stand-up comedy
-- night ("Comedy Night Featuring Clara Bijl", "Comedy Night - Joe Klocek") and a
-- recurring "Open Mic Night" with mostly non-comedy programming (films, plays,
-- youth theatre, dance, concerts, auditions). A title allowlist isolates comedy.
--
-- This wires the generic `squarespace` scraper (no Python change beyond the new
-- shared include_title_patterns filter shipped in this task) with
-- metadata.include_title_patterns scoped to comedy keywords, keeping only the
-- comedy shows. The filter is OFF by default for every existing Squarespace venue.
--
-- A comedy-filtered mixed-use source yields 0 shows when the live feed currently
-- lists no stand-up night (Clayton Club precedent, TASK-3192): comedy auto-populates
-- when the next Comedy Night / Open Mic is listed.
--
-- Idempotent: NOT EXISTS guards on both inserts so the migration no-ops where the
-- rows already exist and reproduces them on a fresh DB.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Cloverdale Performing Arts Center', '209 N Cloverdale Blvd, Cloverdale, CA 95425',
    'https://www.cloverdaleperformingarts.com',
    'Cloverdale', 'CA', '95425', 'America/Los_Angeles', 'US', 'club',
    'ChIJc_Q9827_g4AR8Jixyo4FXFI', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJc_Q9827_g4AR8Jixyo4FXFI'
       OR name = 'Cloverdale Performing Arts Center'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    priority, enabled, metadata, created_at, updated_at
)
SELECT
    c.id,
    'squarespace'::"ScrapingPlatform",
    'squarespace',
    'https://www.cloverdaleperformingarts.com/api/open/GetItemsByMonth?collectionId=66ddfcba655ffa05a0699e3e',
    0,
    TRUE,
    jsonb_build_object(
        'include_title_patterns',
        jsonb_build_array('comedy', 'stand[- ]?up', 'comedian', 'open mic')
    ),
    now(),
    now()
FROM clubs c
WHERE (c.google_place_id = 'ChIJc_Q9827_g4AR8Jixyo4FXFI' OR c.name = 'Cloverdale Performing Arts Center')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'squarespace'
  )
  -- Also guard the table's real unique key (club_id, platform, priority) so a
  -- pre-existing 'squarespace'/priority-0 row for this club can't make the
  -- NOT-EXISTS-on-scraper_key guard pass and then trip a constraint violation.
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.platform = 'squarespace'::"ScrapingPlatform" AND s.priority = 0
  );
