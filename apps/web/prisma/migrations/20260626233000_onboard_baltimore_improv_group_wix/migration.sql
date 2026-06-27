-- Onboard Baltimore Improv Group / BIG (Baltimore, MD) — TASK-3335,
-- objective #9 discover-comedy-venues near Baltimore 21201.
--
-- Baltimore Improv Group (bigimprov.org) is a dedicated improv theater. Its
-- /shows page embeds a native **Wix Events** viewer widget (events-viewer
-- bundle) that lists its ticketed shows (FAM Fest, Tabletop Live, gameshows,
-- etc.) linking to bigimprov.org/event-details-registration/<slug>. The existing
-- generic `wix_events` scraper handles this: it reads the venue root from
-- source_url and the events-widget component id from `wix_event_id`, then queries
-- Wix's `paginated-events/viewer` API.
--
-- The events-widget compId (`comp-leugmrs64`) was found via Playwright as the
-- innermost `comp-*` ancestor of an event-details link on /shows.
--
-- Fixed VENUE (its own theater) -> visible=true. The discovery sweep also turned
-- up a separate "Baltimore Improv Festival" place_id
-- (ChIJma4_pgcFyIkRoF2m10XGX3o) at the SAME address — that is a BIG-hosted event,
-- not a distinct venue, so the clubs guard below also excludes it to prevent a
-- duplicate club on a fresh-DB reproduction.
--
-- Verification: validated end-to-end against the LIVE Wix Events API — 14 shows
-- scraped/persisted ($10.25, dates through 2026-09).
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible). Guard on name OR either place_id (venue +
-- the BIG-hosted festival place_id at the same address).
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Baltimore Improv Group',
       '1727 N Charles St',
       'https://www.bigimprov.org/',
       'Baltimore', 'MD', '21201',
       'America/New_York', 'US', 'club',
       'ChIJ10OU8eoEyIkRd12h4Gymxos',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'Baltimore Improv Group'
     OR google_place_id IN ('ChIJ10OU8eoEyIkRd12h4Gymxos', 'ChIJma4_pgcFyIkRoF2m10XGX3o')
);

-- 2. The wix_events scraping source (venue root + events-widget compId).
-- platform 'wix_events' is a curated enum value; the scraper reads the compId
-- from wix_event_id. Locate the club by name OR google_place_id for idempotency
-- parity with the guard above.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, wix_event_id, priority, enabled, metadata)
SELECT c.id, 'wix_events', 'wix_events',
       'https://www.bigimprov.org',
       'comp-leugmrs64',
       0, true, '{}'::jsonb
FROM clubs c
WHERE (c.name = 'Baltimore Improv Group' OR c.google_place_id = 'ChIJ10OU8eoEyIkRd12h4Gymxos')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'wix_events'
  );
