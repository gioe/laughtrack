-- Onboard The Hive Black Box Theater (Pompano Beach, FL) — TASK-3360,
-- objective #11 discover-comedy-venues near Miami 33130.
--
-- The discovery task targeted the Pompano Beach Cultural Center, but that venue
-- hosts no stand-up/improv (only music tributes, musical theater, exhibitions,
-- and art classes). The real recurring comedy in the Pompano Beach Arts network
-- ("Live at the Hive: Florida's Funniest Comedians") runs in a SIBLING room —
-- The Hive Black Box Theater, inside the Ali Cultural Arts Center — on the same
-- scrapable platform. So we onboard The Hive, not the Cultural Center.
--
-- Platform: the municipal arts site pompanobeacharts.org serves one /events page
-- listing all programs across five rooms as bare <a href="/events/<slug>"> cards
-- (no Event JSON-LD on the listing); each detail page embeds one schema.org Event
-- block. The existing generic `json_ld` scraper handles it in detail_fetch anchor
-- mode (url_path_prefix=/events/). The detail-page Event blocks carry
-- name/startDate/location.name but NO url, so set_same_as_to_detail_url supplies
-- the fetched detail URL as the event url (json_ld extractor change shipped in the
-- same task — JsonLdEvent requires url and would otherwise drop the event).
--
-- Filters: location_name_filter="The Hive Black Box Theater" isolates the Hive
-- from the 56-event multi-room feed; comedy_filter drops the Hive's own dance
-- classes / open mics / concert series, keeping only the stand-up.
--
-- Fixed VENUE -> visible=true. No google_place_id (the discovery place_id belongs
-- to the Cultural Center, a different venue), so the idempotency guard keys on the
-- unique club name only.
--
-- Verification: validated end-to-end against the LIVE feed and prod DB — the
-- two filters isolated the "Live at the Hive: Florida's Funniest Comedians"
-- stand-up series (1 comedy show in the current window; club 11459, source 7027),
-- show_page_url pointing at the venue's own /events/live-at-the-hive page. More
-- surface as the recurring series rolls forward nightly.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible). Guard on the unique club name.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, visible, status)
SELECT 'The Hive Black Box Theater',
       '355 Dr. Martin Luther King Jr. Blvd, Pompano Beach, FL 33060',
       'https://www.pompanobeacharts.org/ali-cultural-arts/thehive',
       'Pompano Beach', 'FL', '33060',
       'America/New_York', 'US', 'club',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs WHERE name = 'The Hive Black Box Theater'
);

-- 2. The json_ld scraping source: /events listing in detail_fetch anchor mode,
-- with url injection (set_same_as_to_detail_url), venue isolation
-- (location_name_filter), and comedy isolation (comedy_filter).
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom', 'json_ld',
       'https://www.pompanobeacharts.org/events',
       0, true,
       jsonb_build_object(
         'detail_fetch', jsonb_build_object(
           'enabled', true,
           'url_path_prefix', '/events/',
           'set_same_as_to_detail_url', true
         ),
         'location_name_filter', 'The Hive Black Box Theater',
         'comedy_filter', true
       )
FROM clubs c
WHERE c.name = 'The Hive Black Box Theater'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'json_ld'
  );
