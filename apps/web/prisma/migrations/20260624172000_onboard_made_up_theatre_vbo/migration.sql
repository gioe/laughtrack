-- Onboard Made Up Theatre (Fremont, CA) via the generic vbo_tickets scraper - TASK-3253.
--
-- Made Up Theatre is a comedy/improv venue whose VBO ListEvents listing
-- collapses concrete occurrences into open-ended text such as "Saturdays at
-- 8:00pm" and "Select Sundays at 2:30pm". The generic `vbo_tickets` scraper
-- now expands those rows from VBO's per-event date-slider endpoint, so the
-- venue can use the shared scraper without fabricating recurrence dates from
-- listing copy.
--
-- VBO SiteID: D482C84A-72F2-42C7-927A-63219F86F013
-- Google place_id: ChIJuwbpqSDHj4ARfEATPFfELwg
-- Metadata keeps only "MUT Shows" and drops non-show VBO categories.
--
-- Idempotent: guarded club/source inserts so reruns and fresh DBs converge.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Made Up Theatre',
    '4000 Bay St, Fremont, CA 94538',
    'https://madeuptheatre.com',
    'Fremont',
    'CA',
    '94538',
    'America/Los_Angeles',
    'US',
    'club',
    'ChIJuwbpqSDHj4ARfEATPFfELwg',
    TRUE,
    'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJuwbpqSDHj4ARfEATPFfELwg'
       OR name = 'Made Up Theatre'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    priority, enabled, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'vbo_tickets',
    'https://plugin.vbotickets.com/plugin/loadplugin?siteid=D482C84A-72F2-42C7-927A-63219F86F013&page=ListEvents',
    0,
    TRUE,
    '{"category_filter": "MUT Shows"}'::jsonb,
    now(),
    now()
FROM clubs c
WHERE (c.google_place_id = 'ChIJuwbpqSDHj4ARfEATPFfELwg' OR c.name = 'Made Up Theatre')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'vbo_tickets'
  )
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.platform = 'custom'::"ScrapingPlatform" AND s.priority = 0
  );
