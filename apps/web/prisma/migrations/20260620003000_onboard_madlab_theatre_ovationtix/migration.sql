-- Onboard MadLab Theatre (Columbus, OH) — TASK-2925
--
-- MadLab Theatre (227 N 3rd St, Columbus, OH 43215; madlab.net) is a Columbus
-- improv/sketch-comedy theater. Surfaced during TASK-2883 (Columbus Improv Wars):
-- Improv Wars is a roving producer whose shows are staged at MadLab and ticketed
-- via OvationTix. MadLab's own improv company (Blank Slate Theatre) also performs
-- here. Fixed venue → visible=TRUE.
--
-- Datasource: OvationTix, client id 35811. The venue's own site (madlab.net)
-- links ci.ovationtix.com client 35811 production widgets; the OvationTix calendar
-- page (web.ovationtix.com/trs/cal/35811) is the supported discovery URL. Handled
-- by the existing generic `ovationtix` scraper. Per convention #188, OvationTix
-- productions carry a hiddenUntil date and only surface on the calendar once
-- on-sale, so the nightly scraper picks up more shows as productions un-hide.
-- Verified: 11 shows scraped in prod (incl. Blank Slate Theatre improv).
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, visible, status)
SELECT 'MadLab Theatre', '227 N 3rd St, Columbus, OH 43215', 'https://madlab.net', 'Columbus', 'OH', '43215', 'America/New_York', 'US', 'club', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'MadLab Theatre');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, ovationtix_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'ovationtix'::"ScrapingPlatform", 'ovationtix', 'https://web.ovationtix.com/trs/cal/35811', '35811', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'MadLab Theatre'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'ovationtix');
