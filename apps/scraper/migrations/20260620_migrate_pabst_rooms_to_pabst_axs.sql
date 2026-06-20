-- TASK-3035: Migrate Pabst Theater Group rooms to the pabst_axs scraper.
--
-- TASK-3033 shipped the pabst_axs venue-page scraper (reusable across the Pabst
-- Theater Group) and onboarded The Riverside Theater. This migration migrates the
-- two sibling rooms:
--   1. Pabst Theater (existing club 5096, currently on ticketmaster_comedy) — add a
--      pabst_axs source on its venue page and disable the ticketmaster_comedy source
--      (TM only cross-lists ~1 comedy event for these venues; the venue page carries
--      the full comedy slate).
--   2. Turner Hall Ballroom (not yet a club) — onboard fresh with pabst_axs.
--
-- Both rooms are music-dominated, so each source opts into the shared comedy filter
-- (comedy_filter keeps comedy-keyword titles + known comedians above the popularity
-- floor; comedy_title_allowlist force-keeps the confirmed comedian-name acts the
-- keyword filter misses). Verified via a real scrape (TASK-3035): Pabst Theater = 5
-- dated comedy shows (Jonathan Van Ness, Derrick Stroup, Kevin Smith, Small Town
-- Murder, Daniel Sloss); Turner Hall = 3 (Ron Funches, Zarna Garg, Robby Hoffman).
--
-- Idempotent: clubs keyed on google_place_id (fallback case-insensitive name);
-- scraping_sources keyed on (club_id, scraper_key).

-- ── 1. Pabst Theater (existing club 5096) ───────────────────────────────────────
--
-- Order matters: the partial unique index
-- `scraping_sources_club_priority_enabled_unique (club_id, priority) WHERE enabled`
-- only allows one ENABLED source per (club_id, priority). The existing
-- ticketmaster_comedy row sits at priority 0, so disable it BEFORE inserting the
-- enabled pabst_axs row at priority 0.

-- Disable the old ticketmaster_comedy source now that pabst_axs is confirmed working.
UPDATE scraping_sources s
   SET enabled = FALSE,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.scraper_key = 'ticketmaster_comedy'
   AND (c.google_place_id = 'ChIJkx8YRgoZBYgRC5EHV8w7gIg'
        OR lower(c.name) = lower('Pabst Theater'));

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, priority, enabled, metadata
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'pabst_axs',
    'https://pabsttheater.org/venues/the-pabst-theater/',
    0,
    TRUE,
    '{"default_show_time": "19:00", "comedy_filter": true, "comedy_title_allowlist": ["derrick stroup", "daniel sloss", "small town murder", "jonathan van ness", "kevin smith"]}'::jsonb
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJkx8YRgoZBYgRC5EHV8w7gIg'
        OR lower(c.name) = lower('Pabst Theater'))
   AND NOT EXISTS (
       SELECT 1 FROM scraping_sources s
        WHERE s.club_id = c.id AND s.scraper_key = 'pabst_axs'
   );

UPDATE scraping_sources s
   SET platform = 'custom'::"ScrapingPlatform",
       source_url = 'https://pabsttheater.org/venues/the-pabst-theater/',
       priority = 0,
       enabled = TRUE,
       metadata = '{"default_show_time": "19:00", "comedy_filter": true, "comedy_title_allowlist": ["derrick stroup", "daniel sloss", "small town murder", "jonathan van ness", "kevin smith"]}'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.scraper_key = 'pabst_axs'
   AND (c.google_place_id = 'ChIJkx8YRgoZBYgRC5EHV8w7gIg'
        OR lower(c.name) = lower('Pabst Theater'));

-- ── 2. Turner Hall Ballroom (new club) ──────────────────────────────────────────

INSERT INTO clubs (
    name, address, website, zip_code, timezone, visible,
    city, state, status, club_type, google_place_id
)
SELECT
    'Turner Hall Ballroom',
    '1040 N Vel R. Phillips Ave',
    'https://pabsttheater.org/venues/turner-hall-ballroom/',
    '53203',
    'America/Chicago',
    TRUE,
    'Milwaukee',
    'WI',
    'active',
    'theater',
    'ChIJuVXrXOsZBYgRA-bajDMIVHI'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
     WHERE google_place_id = 'ChIJuVXrXOsZBYgRA-bajDMIVHI'
        OR lower(name) = lower('Turner Hall Ballroom')
);

UPDATE clubs
   SET address = '1040 N Vel R. Phillips Ave',
       website = 'https://pabsttheater.org/venues/turner-hall-ballroom/',
       zip_code = '53203',
       timezone = 'America/Chicago',
       visible = TRUE,
       city = 'Milwaukee',
       state = 'WI',
       status = 'active',
       club_type = 'theater',
       google_place_id = COALESCE(google_place_id, 'ChIJuVXrXOsZBYgRA-bajDMIVHI')
 WHERE google_place_id = 'ChIJuVXrXOsZBYgRA-bajDMIVHI'
    OR lower(name) = lower('Turner Hall Ballroom');

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, priority, enabled, metadata
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'pabst_axs',
    'https://pabsttheater.org/venues/turner-hall-ballroom/',
    0,
    TRUE,
    '{"default_show_time": "19:00", "comedy_filter": true, "comedy_title_allowlist": ["ron funches", "zarna garg", "robby hoffman"]}'::jsonb
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJuVXrXOsZBYgRA-bajDMIVHI'
        OR lower(c.name) = lower('Turner Hall Ballroom'))
   AND NOT EXISTS (
       SELECT 1 FROM scraping_sources s
        WHERE s.club_id = c.id AND s.scraper_key = 'pabst_axs'
   );

UPDATE scraping_sources s
   SET platform = 'custom'::"ScrapingPlatform",
       source_url = 'https://pabsttheater.org/venues/turner-hall-ballroom/',
       priority = 0,
       enabled = TRUE,
       metadata = '{"default_show_time": "19:00", "comedy_filter": true, "comedy_title_allowlist": ["ron funches", "zarna garg", "robby hoffman"]}'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.scraper_key = 'pabst_axs'
   AND (c.google_place_id = 'ChIJuVXrXOsZBYgRA-bajDMIVHI'
        OR lower(c.name) = lower('Turner Hall Ballroom'));
