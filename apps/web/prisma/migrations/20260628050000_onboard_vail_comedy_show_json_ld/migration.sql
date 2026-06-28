-- Onboard "Vail Comedy Show" (Vail, CO) — TASK-3450,
-- objective discover-comedy-venues near Denver 80202.
--
-- Datasource: the venue's own site https://www.vailcomedyshow.com/ lists its
-- upcoming productions, each a www.comedyticketing.com event-detail page (the
-- Mark Masters Comedy platform, same backend as TASK-3435 Breckenridge Comedy
-- Show) that emits clean schema.org Event JSON-LD (name/startDate/location/
-- offers/performers). Confirmed comedy: named touring comedians (Andrew
-- Orvedahl, Kellen Erskine, Rojo Perez, Steven Gillespie). All event links carry
-- the ?affiliate=vcswww tag, so the page lists ONLY Vail Comedy Show productions.
--
-- Wiring: generic `json_ld` scraper in detail_fetch anchor mode — fetch the
-- vailcomedyshow.com index, collect the `/events/` anchors whose host is
-- comedyticketing.com, fetch each detail page, and extract its Event JSON-LD.
--
-- No location_name_filter (unlike Breckenridge, which filtered a shared producer
-- Linktree by town): Vail Comedy Show is a roving brand that pops up across Eagle
-- County (Vail Village / Cucina at Lodge at Vail, Westin Avon, Eagle River
-- Brewing in Gypsum). The source page is VCS-specific, so every linked event is a
-- VCS production; a "Vail" town filter would wrongly drop the Avon/Gypsum pop-ups.
-- All shows attach to this one visible "Vail Comedy Show" club (roving-brand-as-
-- single-club), each show_page_url its comedyticketing.com event page.
--
-- Verification: a json_ld detail_fetch scrape returned 3 comedy shows; a real
-- `make scrape-club-id ID=<club_id>` persisted them onto this club.
--
-- Idempotent: guarded INSERTs no-op where the club / scraping_sources row exist.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Vail Comedy Show',
    '304 Bridge St, Vail, CO 81657, USA',
    'https://www.vailcomedyshow.com/',
    'Vail', 'CO', '81657', 'America/Denver', 'US', 'club',
    'ChIJWdTYcElxaocRJdzL6KMcMpg', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJWdTYcElxaocRJdzL6KMcMpg'
       OR name = 'Vail Comedy Show'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'json_ld',
    'https://www.vailcomedyshow.com/',
    TRUE,
    0,
    '{"detail_fetch": {"enabled": true, "url_path_prefix": "/events/", "allowed_hosts": ["www.comedyticketing.com", "comedyticketing.com"], "set_same_as_to_detail_url": true}}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJWdTYcElxaocRJdzL6KMcMpg' OR c.name = 'Vail Comedy Show')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'json_ld'
  );
