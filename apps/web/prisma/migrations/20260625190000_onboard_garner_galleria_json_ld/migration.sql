-- Onboard The Garner Galleria Theatre (Denver, CO) — TASK-3388
-- (discover-comedy-venues near 80202).
--
-- The Garner Galleria Theatre is the cabaret room inside the Denver Performing
-- Arts Complex (denvercenter.org). It hosts comedy/improv/cabaret programming
-- (e.g. The Improvised Shakespeare Company, Hold On To Your Butts). The DCPA
-- site exposes a TheaterEvent JSON-LD block on each /tickets-events/<slug>/
-- detail page, so the venue is wired to the generic `json_ld` scraper in
-- listing->detail mode, scoped to this venue via location_name_filter so it
-- stays cleanly separate from the broader complex (TASK-3390).
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Fixed (visible) venue club.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Garner Galleria Theatre',
       '1400 Curtis Street, Denver, CO 80204',
       'https://www.denvercenter.org/',
       'Denver', 'CO', '80204', 'America/Denver', 'US', 'club',
       'ChIJ8xARvM94bIcRPlWLEg0dF4k', true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Garner Galleria Theatre');

-- 2. Generic json_ld scraping source (no unique constraint beyond PK, so guard
--    with NOT EXISTS on (club_id, scraper_key)). detail_fetch walks each
--    /tickets-events/<slug>/ detail page for its TheaterEvent JSON-LD;
--    location_name_filter keeps only shows whose location is the Garner Galleria.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom', 'json_ld',
       'https://www.denvercenter.org/tickets-events/', 0, true,
       '{"location_name_filter": "Garner Galleria Theatre", "detail_fetch": {"enabled": true, "url_path_prefix": "/tickets-events/", "set_same_as_to_detail_url": true, "exclude_url_path_suffixes": ["/tickets-events/", "/dcpa-theatre-classes/", "/public-tours/", "/colorado-new-play-summit/"]}}'::jsonb
FROM clubs c
WHERE c.name = 'The Garner Galleria Theatre'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'json_ld'
  );
