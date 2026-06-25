-- Onboard Scruffy Murphy's (Denver, CO) — TASK-3387, objective #13
-- (discover-comedy-venues near 80202).
--
-- Scruffy Murphy's is an Irish pub at 2030 Larimer St that hosts a weekly
-- "Comedy Open Mic" every Tuesday. The pub's own GoDaddy single-page site
-- (scruffymurphysirishpub.com) advertises the night in prose only — no events
-- page, no calendar, no ticketing widget, no Event JSON-LD — so it is not
-- scrapable directly.
--
-- The comedy night is published as a live recurring Eventbrite series,
-- "The Scruffy Murphy's Comedy Open Mic" (event 1685433861049, status=started),
-- run by Eventbrite organizer "Furious Jorge" (id 115971389631). Wiring the club
-- to the generic `eventbrite` scraper in ORGANIZER mode (source_url contains
-- `/o/`) yields the dated weekly instances. The organizer feed groups events by
-- venue and they all land at Scruffy Murphy's (1 venue), so this is a FIXED
-- venue (visible=true), not a roving-producer proxy.
--
-- NOTE: an older "Scruffy Murphy's Comedy Show" series (organizer Quentin
-- Johnson, id 17388296975) is COMPLETED (2022–2024) and returns 0 events; do
-- NOT use that organizer id.
--
-- Verified: make scrape-club-id => 16 shows (2026-07-01 .. 2026-10-14).
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Venue club (fixed venue, visible).
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Scruffy Murphy''s',
       '2030 Larimer St, Denver, CO 80205, USA',
       'https://scruffymurphysirishpub.com/',
       'Denver', 'CO', '80205', 'America/Denver', 'US', 'club',
       'ChIJ7zlfBNx4bIcRXydx2qGK1-A', true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Scruffy Murphy''s');

-- 2. Eventbrite organizer-mode scraping source (no unique constraint beyond PK,
--    so guard with NOT EXISTS on (club_id, scraper_key)).
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata)
SELECT c.id, 'eventbrite', 'eventbrite',
       'https://www.eventbrite.com/o/furious-jorge-115971389631', '115971389631', 0, true, '{}'
FROM clubs c
WHERE c.name = 'Scruffy Murphy''s'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'eventbrite'
  );
