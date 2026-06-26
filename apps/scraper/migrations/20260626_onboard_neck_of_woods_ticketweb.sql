-- TASK-3252: Onboard Neck of the Woods (San Francisco, CA) via ticketweb with a
-- comedy include_title_patterns allowlist.
--
-- Re-onboarding enabled by TASK-3248. Neck of the Woods (neckofthewoodssf.com,
-- 406 Clement St SF) was closed wont_do in TASK-3181 ONLY because the ticketweb
-- scraper had no genre filter: it is a mixed-use live-music venue whose
-- TicketWeb calendar (~16 events) is dominated by band/metal/punk/DJ shows with
-- a single recurring comedy series threaded through it. TASK-3248 added the
-- opt-in include_title_patterns allowlist, so the venue is now cleanly
-- onboardable.
--
-- Allowlist scoping (verified against the live calendar 2026-06-26):
--   KEEP  'Clement St Comedy'                  — the venue's branded stand-up series (currently listed)
--   KEEP  'Best of San Francisco Stand-up Comedy' — recurring stand-up series named on the
--          prior calendar; between dates now, will auto-populate when next listed (Clayton Club precedent)
--   DROP  everything else — all band/metal/punk/rap/DJ acts.
--   DROP  'Neck of the Woods SF Open Mic Wednesdays' — deliberately EXCLUDED. The
--          task flagged it for confirmation; investigation shows it is a
--          MUSIC-primary open mic (its own Facebook group is "notwmusicsfopenmic";
--          house rules give "Musicians 1 song, Comedians 4 minutes"), i.e. a general
--          open mic that merely allows comics, not a comedy series. Per convention
--          #195, onboarding it would surface a weekly music event as comedy.
--
-- An include-filtered mixed-use source yields 0 shows by design whenever no
-- matching comedy night is currently listed; comedy auto-populates later.
-- Datasource: the venue's OWN calendar page (TicketWeb tw-plugin-upcoming-event-list),
-- platform=custom, scraper_key=ticketweb (see SCRAPERS.md TicketWeb section).

INSERT INTO clubs (
    name,
    address,
    website,
    zip_code,
    timezone,
    visible,
    city,
    state,
    country,
    status,
    club_type,
    google_place_id
)
SELECT
    'Neck of the Woods',
    '406 Clement St',
    'https://www.neckofthewoodssf.com/',
    '94118',
    'America/Los_Angeles',
    TRUE,
    'San Francisco',
    'CA',
    'US',
    'active',
    'club',
    'ChIJs3wUCjyHhYARQlTmEw2aFic'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJs3wUCjyHhYARQlTmEw2aFic'
        OR lower(name) = lower('Neck of the Woods')
);

UPDATE clubs
   SET address = '406 Clement St',
       website = 'https://www.neckofthewoodssf.com/',
       zip_code = '94118',
       timezone = 'America/Los_Angeles',
       visible = TRUE,
       city = 'San Francisco',
       state = 'CA',
       country = 'US',
       status = 'active',
       club_type = 'club',
       google_place_id = COALESCE(google_place_id, 'ChIJs3wUCjyHhYARQlTmEw2aFic')
 WHERE google_place_id = 'ChIJs3wUCjyHhYARQlTmEw2aFic'
    OR lower(name) = lower('Neck of the Woods');

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    priority,
    enabled,
    metadata
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'ticketweb',
    'https://www.neckofthewoodssf.com/calendar/',
    0,
    TRUE,
    jsonb_build_object(
        'include_title_patterns', jsonb_build_array(
            'Clement St\.? Comedy',
            'Best of San Francisco Stand'
        )
    )
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJs3wUCjyHhYARQlTmEw2aFic'
        OR lower(c.name) = lower('Neck of the Woods'))
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.platform = 'custom'::"ScrapingPlatform"
          AND s.priority = 0
   );

UPDATE scraping_sources s
   SET scraper_key = 'ticketweb',
       source_url = 'https://www.neckofthewoodssf.com/calendar/',
       enabled = TRUE,
       metadata = jsonb_build_object(
           'include_title_patterns', jsonb_build_array(
               'Clement St\.? Comedy',
               'Best of San Francisco Stand'
           )
       ),
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.platform = 'custom'::"ScrapingPlatform"
   AND s.priority = 0
   AND (c.google_place_id = 'ChIJs3wUCjyHhYARQlTmEw2aFic'
        OR lower(c.name) = lower('Neck of the Woods'));
