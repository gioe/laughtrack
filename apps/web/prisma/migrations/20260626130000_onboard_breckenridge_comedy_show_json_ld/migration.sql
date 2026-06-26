-- Onboard "Breckenridge Comedy Show" (Eclipse Theater, Breckenridge, CO) — TASK-3435
--
-- Datasource: the venue's own promoted page https://www.breckcomedy.com/ redirects
-- to the Linktree https://linktr.ee/breckenridgecomedy, which lists ONLY this venue's
-- upcoming shows. Each linked show is a comedyticketing.com event-detail page that
-- emits clean schema.org Event JSON-LD (name/url/startDate/location/offers/performers).
--
-- Wiring: generic `json_ld` scraper in detail_fetch anchor mode — fetch the Linktree
-- index, collect the `/events/` anchors whose host is www.comedyticketing.com, fetch
-- each detail page, and extract its Event JSON-LD. `location_name_filter` = "Breckenridge"
-- is a town-scope safety net so any stray non-Breckenridge link on the producer's
-- Linktree is dropped (Mark Masters Comedy LLC also produces shows in other towns).
--
-- Fixed host venue (Eclipse Theater, 103 S Harris St — matches the task address), so
-- the club is inserted visible=true (not a hidden roving-producer proxy).
--
-- Idempotent: guarded INSERTs no-op where the club / scraping_sources row already exist.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Breckenridge Comedy Show',
    '103 S Harris St, Breckenridge, CO 80424, USA',
    'https://www.breckcomedy.com/',
    'Breckenridge', 'CO', '80424', 'America/Denver', 'US', 'club',
    'ChIJCbsCqjH3aocRUwSWjtfSkwg', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJCbsCqjH3aocRUwSWjtfSkwg'
       OR name = 'Breckenridge Comedy Show'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'json_ld',
    'https://linktr.ee/breckenridgecomedy',
    TRUE,
    0,
    '{"location_name_filter": "Breckenridge", "detail_fetch": {"enabled": true, "url_path_prefix": "/events/", "allowed_hosts": ["www.comedyticketing.com"], "set_same_as_to_detail_url": true}}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJCbsCqjH3aocRUwSWjtfSkwg' OR c.name = 'Breckenridge Comedy Show')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'json_ld'
  );
