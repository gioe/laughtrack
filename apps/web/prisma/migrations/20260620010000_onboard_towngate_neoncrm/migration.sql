-- Onboard Oglebay Institute Towngate Theatre & Cinema (Wheeling, WV) — TASK-2939
--
-- Towngate Theatre (2118 Market St, Wheeling WV 26003; oionline.com/towngate/)
-- is a confirmed comedy venue: two resident improv troupes (Left of Centre
-- Players adult, Crazy 8s youth) plus occasional touring stand-up. Fixed venue
-- → visible=TRUE.
--
-- Datasource: Oglebay Institute runs on NeonCRM (Neon One). Its public event
-- list is https://oionline.app.neoncrm.com/eventList.jsp?categoryId=27
-- ("Theater Productions" — the improv/stand-up/plays category). Handled by the
-- NEW generic `neoncrm` scraper, which parses the static event rows
-- (curl_cffi chrome impersonation). platform='custom' (NeonCRM has no dedicated
-- ScrapingPlatform enum value). metadata carries the org slug + category id list
-- so the scraper builds the eventList URL(s) and other NeonCRM venues can reuse
-- it. Verified: 3 upcoming Theater Productions scraped (currently plays; the
-- resident improv/comedy shows appear seasonally under the same category).
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, visible, status, google_place_id)
SELECT 'Oglebay Institute Towngate Theatre & Cinema', '2118 Market Street, Wheeling, WV 26003', 'https://oionline.com/towngate/', 'Wheeling', 'WV', '26003', 'America/New_York', 'US', 'club', TRUE, 'active', 'ChIJ4TOwRYDZNYgRX_i5hwvSiRU'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Oglebay Institute Towngate Theatre & Cinema');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'custom'::"ScrapingPlatform", 'neoncrm', 'https://oionline.app.neoncrm.com/eventList.jsp?categoryId=27', 0, TRUE, '{"neon_org": "oionline", "category_ids": [27]}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Oglebay Institute Towngate Theatre & Cinema'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'neoncrm');
