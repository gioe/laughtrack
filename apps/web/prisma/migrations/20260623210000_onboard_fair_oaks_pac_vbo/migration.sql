-- Onboard Fair Oaks Performing Arts Center (Fair Oaks, CA) via the generic vbo_tickets scraper - TASK-3204.
--
-- Fair Oaks PAC (fairoaksarts.org) is a multi-use performing-arts center that
-- tickets through VBO Tickets (SiteID AB1E7875-362D-4528-A36D-CEBDFC7BEDA9,
-- OrgID 8974) and runs a "Comedy Under the Stars" stand-up series alongside
-- concerts, films, theatre and magic shows. Its VBO category for the comedy
-- nights is the generic "Performing Arts", shared with non-comedy events, so a
-- data-event-category filter can't isolate comedy. Instead this wires the
-- generic `vbo_tickets` scraper with metadata.include_title_patterns scoped to
-- the "Comedy Under the Stars" series, keeping only the comedy shows.
--
-- Verified: a real scrape persisted 3 comedy shows (Keon Polee, Ian Levy,
-- Jon Stringer) with the concerts/films/magic on the same VBO listing dropped.
-- Idempotent: NOT EXISTS guards on both inserts so the migration no-ops where
-- the rows already exist and reproduces them on a fresh DB.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Fair Oaks Performing Arts Center', '7991 California Ave, Fair Oaks, CA 95628',
    'https://www.fairoaksarts.org',
    'Fair Oaks', 'CA', '95628', 'America/Los_Angeles', 'US', 'club',
    'ChIJuZcg3gDdmoARNqMo55x-_Go', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJuZcg3gDdmoARNqMo55x-_Go'
       OR name = 'Fair Oaks Performing Arts Center'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    priority, enabled, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'vbo_tickets',
    'https://plugin.vbotickets.com/plugin/loadplugin?siteid=AB1E7875-362D-4528-A36D-CEBDFC7BEDA9&page=ListEvents',
    0,
    TRUE,
    jsonb_build_object(
        'include_title_patterns',
        jsonb_build_array('Comedy Under the Stars')
    ),
    now(),
    now()
FROM clubs c
WHERE (c.google_place_id = 'ChIJuZcg3gDdmoARNqMo55x-_Go' OR c.name = 'Fair Oaks Performing Arts Center')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'vbo_tickets'
  )
  -- Also guard the table's real unique key (club_id, platform, priority) so a
  -- pre-existing 'custom'/priority-0 row for this club can't make the
  -- NOT-EXISTS-on-scraper_key guard pass and then trip a constraint violation.
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.platform = 'custom'::"ScrapingPlatform" AND s.priority = 0
  );
