-- Onboard The Clocktower Cabaret (Denver, CO) — TASK-3383
-- (discover-comedy-venues near 80202).
--
-- The Clocktower Cabaret is a fixed cabaret/comedy venue at 1601 Arapahoe St
-- whose own site (clocktowercabaret.com/shows) hydrates its show listings from
-- OvationTix (client id 35628 — buy links go to ci.ovationtix.com/35628/...).
-- It is wired to the generic `ovationtix` scraper, which reads the venue's
-- ovationtix client id + calendar URL from the scraping source. Fixed venue, so
-- the club is visible (visible=true) and its shows surface under it directly.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Fixed (visible) venue club.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Clocktower Cabaret',
       '1601 Arapahoe St, Denver, CO 80202, USA',
       'https://www.clocktowercabaret.com/',
       'Denver', 'CO', '80202', 'America/Denver', 'US', 'club',
       'ChIJASbMldp4bIcRiFeLsW3CUf4', true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Clocktower Cabaret');

-- 2. OvationTix scraping source (no unique constraint beyond PK, so guard with
--    NOT EXISTS on (club_id, scraper_key)). The scraper reads ovationtix_id as
--    the client id and source_url as the calendar discovery page.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, ovationtix_id, priority, enabled, metadata)
SELECT c.id, 'ovationtix', 'ovationtix',
       'https://web.ovationtix.com/trs/cal/35628', '35628', 0, true, '{}'
FROM clubs c
WHERE c.name = 'The Clocktower Cabaret'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'ovationtix'
  );
