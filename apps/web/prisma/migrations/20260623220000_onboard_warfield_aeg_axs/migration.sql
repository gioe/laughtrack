-- Onboard The Warfield (San Francisco, CA) via the net-new aeg_axs scraper - TASK-3209.
--
-- The Warfield (982 Market St, SF) is an AEG Presents / Goldenvoice concert hall.
-- It is overwhelmingly a music venue but occasionally hosts touring stand-up
-- comedy (e.g. "The Kevin Langue Show: Live!", a national comedy tour).
--
-- Datasource (verified 2026-06-23): the venue runs the stock Carbonhouse
-- venue-site template (generatorAgent http://carbonhouse.com/) and tickets every
-- show via AXS (axs.com/events/<id>/...?skin=warfield). The axs.com detail pages
-- are DataDome-protected, but the venue's own /events page is plain
-- server-rendered HTML listing each upcoming show as a div.entry card carrying
-- the name, a real date, a real show time, the venue detail URL, and the AXS
-- ticket link. The new aeg_axs scraper parses that page (distinct from the
-- generic 'axs' rsCaption homepage skin and the 'pabst_axs' div.eventItem
-- template). source_url = the /events page; platform = custom (AXS has no enum).
--
-- Mixed-use venue: the /events page is concert-dominated (19 of 20 upcoming shows
-- are music), so the source opts into the shared comedy_filter to keep only
-- comedy. "The Kevin Langue Show: Live!" carries no comedy keyword and Kevin
-- Langue's stored popularity (0.188) is below the 0.30 known-comedian floor, so a
-- per-source comedy_title_allowlist entry ("kevin langue") keeps it. The venue
-- /events card always carries a real show time (span.time, e.g. "Show 8:00 PM"),
-- so no default_show_time override is set — the entity's 19:00 fallback would
-- only apply to a card with no parseable time, which the Warfield template
-- never produces.
--
-- VERIFICATION NOTE: a real scrape persists a show only while the Warfield is
-- actively listing a comedy date in its /events window. The enabled
-- scraping_sources row means the scraper automatically picks up future comedy as
-- the venue posts it; concerts are dropped by the comedy filter.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'The Warfield', '982 Market St, San Francisco, CA 94102, USA',
    'https://www.thewarfieldtheatre.com/',
    'San Francisco', 'CA', '94102', 'America/Los_Angeles', 'US', 'venue',
    'ChIJ26vXqYWAhYAR-pHMSmLA0nA', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJ26vXqYWAhYAR-pHMSmLA0nA'
       OR name = 'The Warfield'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'aeg_axs',
    'https://www.thewarfieldtheatre.com/events',
    TRUE,
    0,
    '{"comedy_filter": true, "comedy_title_allowlist": ["kevin langue"]}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJ26vXqYWAhYAR-pHMSmLA0nA' OR c.name = 'The Warfield')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'aeg_axs'
  );
