-- Onboard Ohio Star Theater at Dutch Valley (Sugarcreek, OH) — TASK-2896
--
-- Discovered via the discover-comedy-venues skill (objective #2, ZIP 44622).
-- The Ohio Star Theater is the resident theater at Dutch Valley; it programs
-- music, tribute acts, and recurring touring stand-up comedy (e.g. Jeff Allen,
-- OvationTix client 35490 production 1244650). Fixed venue → visible=TRUE.
--
-- Datasource: OvationTix, client id 35490. The venue's own site
-- (ohiostartheater.com) hydrates its listings via OvationTix widgets but exposes
-- only featured production links in static HTML; the OvationTix calendar page
-- (web.ovationtix.com/trs/cal/35490) is the supported discovery URL. Handled by
-- the existing generic `ovationtix` scraper. Most productions carry an OvationTix
-- `hiddenUntil` date and surface on the calendar once on-sale, so the nightly
-- scraper picks them up as they un-hide. Verified: 116 shows scraped in prod.
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Ohio Star Theater at Dutch Valley', '1387 Old Route 39, Sugarcreek, OH 44681', 'https://ohiostartheater.com', 'Sugarcreek', 'OH', '44681', 'America/New_York', 'US', 'club', 'ChIJyctQmF4bN4gRHZxvrvrvVLA', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Ohio Star Theater at Dutch Valley');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, ovationtix_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'ovationtix'::"ScrapingPlatform", 'ovationtix', 'https://web.ovationtix.com/trs/cal/35490', '35490', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Ohio Star Theater at Dutch Valley'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'ovationtix');
