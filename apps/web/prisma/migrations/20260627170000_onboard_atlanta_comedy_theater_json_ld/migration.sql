-- Onboard Atlanta Comedy Theater (Norcross, GA) — TASK-3368,
-- objective #12 discover-comedy-venues near Atlanta 30303.
--
-- Atlanta Comedy Theater is an all-comedy club (national headliners + recurring
-- shows: Majah Hype, TK Kirkland, Shuler King, David C Smalley, ...). Its own
-- site (atlcomedytheater.com/norcross-tickets) is a plain link list — each show
-- links out to a ShowClix / LeapEvents event page (ShowClix migrated its ticket
-- host to events.leapevents.com; www.showclix.com/event/<slug> 302-redirects
-- there). The venue page itself carries no Event JSON-LD, but every
-- ShowClix/LeapEvents event page embeds one schema.org Event block (name,
-- startDate, location "Atlanta Comedy Club", url).
--
-- Datasource: wired to the existing generic `json_ld` scraper in detail_fetch
-- ANCHOR mode with cross-host allowed_hosts — no net-new scraper needed:
--   source_url = the venue's own /norcross-tickets link list
--   detail_fetch.url_path_prefix = '/event/'
--   detail_fetch.allowed_hosts = [events.leapevents.com, www.showclix.com]
-- The scraper harvests the external /event/ links off the venue page, fetches
-- each event page, and parses its Event JSON-LD (url present, so no
-- set_same_as_to_detail_url needed). All events are at this one venue and all
-- comedy -> no location_name_filter, no comedy_filter.
--
-- Fixed venue -> visible=true.
--
-- Verification: `make scrape-club-id ID=<club_id>` found 24 detail pages and
-- scraped 24 comedy shows (club 11466, source 7034), each show_page_url on the
-- LeapEvents event page.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible). Guard on name OR google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Atlanta Comedy Theater',
       '4650 Jimmy Carter Blvd #114b, Norcross, GA 30093',
       'https://atlcomedytheater.com',
       'Norcross', 'GA', '30093',
       'America/New_York', 'US', 'club',
       'ChIJU1hRpoem9YgRtULu172YMz0',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'Atlanta Comedy Theater'
     OR google_place_id = 'ChIJU1hRpoem9YgRtULu172YMz0'
);

-- 2. The json_ld scraping source: venue link list in detail_fetch anchor mode,
-- harvesting the external ShowClix/LeapEvents /event/ links. Locate the club by
-- name OR google_place_id for idempotency parity.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom', 'json_ld',
       'https://atlcomedytheater.com/norcross-tickets',
       0, true,
       jsonb_build_object(
         'detail_fetch', jsonb_build_object(
           'enabled', true,
           'url_path_prefix', '/event/',
           'allowed_hosts', jsonb_build_array('events.leapevents.com', 'www.showclix.com')
         )
       )
FROM clubs c
WHERE (c.name = 'Atlanta Comedy Theater' OR c.google_place_id = 'ChIJU1hRpoem9YgRtULu172YMz0')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'json_ld'
  );
