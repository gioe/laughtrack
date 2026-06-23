-- Onboard Eclectic Box SF (San Francisco, CA) via the new elfsight scraper - TASK-3179.
--
-- Eclectic Box is a 70-seat black box theatre in the Mission (improv, comedy,
-- parody, burlesque, drama, film). Its Squarespace site embeds an Elfsight
-- Event Calendar widget (NOT a native Squarespace events collection); the calendar
-- is Google-Calendar-backed and served from Elfsight's anonymous JSON API. The
-- new generic `elfsight` scraper boots the widget for a fresh token, fetches the
-- events API, and (because the venue is mixed-use) applies the comedy_filter to
-- drop non-comedy programming.
--
-- DB config: source_url is the venue's own calendar page (show_page_url);
-- metadata.widget_pid is the Elfsight widget id (the boot `w` parameter);
-- metadata.comedy_filter=true drops film/music/drama via the comedy keyword allowlist.
--
-- NOTE (verified 2026-06-23): a real scrape extracts and persists 5 upcoming
-- comedy shows (The BOAT Improv Jam series), with ticket links lifted from each
-- event's description HTML.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Eclectic Box SF', '446 Valencia St, San Francisco, CA 94103, USA',
    'https://www.eclecticboxsf.com/',
    'San Francisco', 'CA', '94103', 'America/Los_Angeles', 'US', 'club',
    'ChIJb3G5hP5_j4AR4Uyzd2HaehA', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJb3G5hP5_j4AR4Uyzd2HaehA'
       OR name = 'Eclectic Box SF'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'elfsight',
    'https://www.eclecticboxsf.com/event-calendar',
    TRUE,
    0,
    jsonb_build_object(
        'widget_pid', '619cbb71-bc8f-4451-898d-bc03284f431c',
        'comedy_filter', true
    ),
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJb3G5hP5_j4AR4Uyzd2HaehA' OR c.name = 'Eclectic Box SF')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'elfsight'
  );
