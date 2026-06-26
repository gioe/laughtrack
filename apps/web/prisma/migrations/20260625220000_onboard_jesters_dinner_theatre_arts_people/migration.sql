-- Onboard Jesters Dinner Theatre (Longmont, CO) — TASK-3419, objective #13
-- (discover-comedy-venues near 80202).
--
-- Jesters Dinner Theatre is a fixed venue at 224 Main St whose own site
-- (jesterstheatre.com) is a client-rendered SPA. Its shows are sold through the
-- Arts-People (Neon One) ticketing platform under org slug `jest`:
--   list page:  https://app.arts-people.com/index.php?ticketing=jest
--   per-show:   https://app.arts-people.com/index.php?show=<id>
-- The list page renders each current production as a row in
-- `table.htable_front_page` (title <h1> + a "Buy tickets" link to ?show=<id>);
-- the per-show page lists each bookable performance date inside
-- `#TBLperformances`. Both are static HTML (curl_cffi suffices) — no API key or
-- JS rendering.
--
-- It is primarily a dinner theatre (musicals/plays — e.g. "Brigadoon"), but runs
-- a recurring stand-up/improv series, "Front deRanged Improv Comedy" (OxyMorons
-- troupe), with real dated performances (e.g. Sat Jul 11, 2026 7:30 pm). No
-- existing scraper matched Arts-People, so this ships a new GENERIC `arts_people`
-- scraper (apps/scraper/.../scrapers/implementations/api/arts_people/).
--
-- Because the org mixes musicals with comedy, the source carries an opt-in
-- `include_title_patterns` comedy allowlist so only the comedy production(s) are
-- scraped (the filter is OFF by default for pure-comedy Arts-People orgs). A
-- future Arts-People venue needs only a scraping_sources row with
-- source_url = its ?ticketing=<shortName> page (+ optional title filters).
--
-- Fixed venue (its own room) => visible=true.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Venue club (fixed venue, visible).
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Jesters Dinner Theatre',
       '224 Main St, Longmont, CO 80501, USA',
       'https://jesterstheatre.com',
       'Longmont', 'CO', '80501', 'America/Denver', 'US', 'club',
       'ChIJ7deIh5_5a4cR5Qj6rdBPvfs', true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Jesters Dinner Theatre');

-- 2. Arts-People scraping source (no unique constraint beyond PK, so guard with
--    NOT EXISTS on (club_id, scraper_key)). source_url = ?ticketing list page;
--    include_title_patterns keeps only the comedy production(s).
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom', 'arts_people',
       'https://app.arts-people.com/index.php?ticketing=jest', 0, true,
       '{"include_title_patterns": ["comedy", "improv", "stand[ -]?up", "comedian", "open mic"]}'::jsonb
FROM clubs c
WHERE c.name = 'Jesters Dinner Theatre'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'arts_people'
  );
