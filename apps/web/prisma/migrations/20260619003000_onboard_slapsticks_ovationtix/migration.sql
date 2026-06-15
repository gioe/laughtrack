-- Onboard Slapsticks Comedy Club / Funny Fundraiser (Pittsburgh, PA area) — TASK-2873
--
-- Slapsticks Productions is a ROVING comedy producer: its "Funny Fundraiser"
-- shows run at varying host venues across PA/WV (South Park, Irwin, Hermitage,
-- Morgantown WV, etc.), not at a single fixed address. It is therefore inserted
-- as a hidden synthetic proxy (visible=FALSE); its shows surface under the
-- auto-created per-venue clubs.
--
-- Datasource: OvationTix, client id 36412. The club's own site
-- (slapsticksproductions.com) hydrates its listings via OvationTix widgets but
-- exposes no production links in static HTML; the OvationTix calendar page
-- (web.ovationtix.com/trs/cal/36412) is the supported discovery URL. Handled by
-- the existing generic `ovationtix` scraper. Verified: 8 shows scraped.
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Slapsticks Comedy Club / Funny Fundraiser', '4480 Steubenville Pike, Pittsburgh, PA 15205, USA', 'https://slapsticksproductions.com/', 'Pittsburgh', 'PA', 'America/New_York', 'US', 'club', 'ChIJj3WvDHD2NIgRwVty-Va98vA', FALSE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Slapsticks Comedy Club / Funny Fundraiser');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, ovationtix_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'ovationtix'::"ScrapingPlatform", 'ovationtix', 'https://web.ovationtix.com/trs/cal/36412', '36412', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Slapsticks Comedy Club / Funny Fundraiser'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'ovationtix');
