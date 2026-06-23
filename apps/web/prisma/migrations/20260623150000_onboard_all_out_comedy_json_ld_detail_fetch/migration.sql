-- Onboard All Out Comedy Theater (Oakland, CA) via the json_ld scraper in detail-fetch mode - TASK-3185.
--
-- All Out Comedy Theater is an improv + stand-up comedy theater (2550 Telegraph Ave).
-- Its Squarespace site lists shows on /shows as buttons linking to individual
-- Humanitix event pages (events.humanitix.com/<slug>); the page itself carries no
-- event JSON-LD, and the org exposes no Humanitix host/collections page. So this
-- uses the generic `json_ld` scraper in detail-fetch mode: it fetches the /shows
-- index, collects the Humanitix event anchors (allowed_hosts), then fetches each
-- event page and extracts its (multi-date) schema.org Event JSON-LD. No code needed.
--
-- metadata.detail_fetch:
--   url_path_prefix='/'                         -> every event slug lives at the root
--   allowed_hosts=['events.humanitix.com']       -> only follow Humanitix anchors
--   set_same_as_to_detail_url=true               -> show_page_url points at the event page
--
-- NOTE (verified 2026-06-23): a real scrape follows 5 Humanitix event pages and
-- persists 17 upcoming improv comedy shows (showcases, graduation shows, open jam).

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'All Out Comedy Theater', '2550 Telegraph Ave, Oakland, CA 94612, USA',
    'https://www.alloutcomedytheater.com/',
    'Oakland', 'CA', '94612', 'America/Los_Angeles', 'US', 'club',
    'ChIJK6ZKhVGHj4ARBGsOfj3QAdE', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJK6ZKhVGHj4ARBGsOfj3QAdE'
       OR name = 'All Out Comedy Theater'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'json_ld',
    'https://www.alloutcomedytheater.com/shows',
    TRUE,
    0,
    jsonb_build_object(
        'detail_fetch', jsonb_build_object(
            'url_path_prefix', '/',
            'allowed_hosts', jsonb_build_array('events.humanitix.com'),
            'set_same_as_to_detail_url', true
        )
    ),
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJK6ZKhVGHj4ARBGsOfj3QAdE' OR c.name = 'All Out Comedy Theater')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'json_ld'
  );
