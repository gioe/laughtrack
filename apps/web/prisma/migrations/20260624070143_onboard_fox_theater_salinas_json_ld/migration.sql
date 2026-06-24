-- Onboard Fox Theater Salinas (Salinas, CA) via the existing json_ld scraper - TASK-3242.
--
-- Fox Theater Salinas (foxtheatersalinas.com) is a historic multi-use theater at
-- 241 S Main St, Salinas. Its own Squarespace site (collection 564e474be4b052ed0de24c56)
-- is NOT a Squarespace Events collection: the Events page (/new-page) is a hand-authored
-- content page (typeName=page, GetItemsByMonth returns []) whose "PURCHASE TICKETS"
-- buttons link OUT to the venue's box office, tickets831.com.
--
-- tickets831.com is a Ticketor (ticketor.com) white-label, regional multi-venue box
-- office for the Monterey/831 area. Its homepage embeds one schema.org Event JSON-LD
-- block per upcoming event across ALL its venues, each with location.name + startDate
-- + offers. Confirmed comedy at this venue (verified 2026-06-24): "Richard Villa"
-- (bilingual stand-up comedian) 2026-07-24 and "The Uncle Louie Variety Show" (Italian-
-- American comedy duo Carlo Russo & Lou Greco) 2026-07-25, alongside non-comedy music
-- programming (Capybara Rave/EDM, Grupo Sin Control, a Pink Floyd tribute, etc.).
--
-- Scraper: the generic json_ld scraper, pointed at the Ticketor homepage. Because the
-- homepage is MULTI-VENUE, metadata.location_name_filter='FOX THEATER' keeps only this
-- venue's events (matches "SALINAS FOX THEATER"). Because the venue is MIXED-USE and
-- Ticketor JSON-LD carries no genre/category, metadata.comedy_filter=true isolates
-- comedy via the shared select_comedy_titles heuristic (keyword OR allowlist OR a known
-- comedian above min_comedian_popularity). Tunings:
--   * min_comedian_popularity=0.25 — Richard Villa is in the comedians table at stored
--     popularity 0.2716, just under the 0.30 default; 0.25 keeps him while still
--     dropping data-quality false positives.
--   * comedy_title_allowlist=["uncle louie","variety show"] — the Uncle Louie comedy
--     duo is a confirmed stand-up/variety comedy act not (yet) in the comedians DB and
--     its title carries no comedy keyword, so an allowlist substring keeps it.
-- Non-comedy music events are dropped. A future touring comedian above the floor
-- auto-populates with no further config.
--
-- Idempotent: guarded by NOT EXISTS on google_place_id / name (clubs) and
-- (club_id, scraper_key) (scraping_sources), so re-runs and fresh DBs converge.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Fox Theater Salinas', '241 S Main St, Salinas, CA 93901, USA',
    'http://foxtheatersalinas.com/',
    'Salinas', 'CA', '93901', 'America/Los_Angeles', 'US', 'club',
    'ChIJN28z2MH4jYARN6RkmvjuQG0', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJN28z2MH4jYARN6RkmvjuQG0'
       OR name = 'Fox Theater Salinas'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'json_ld',
    'https://www.tickets831.com/',
    TRUE,
    0,
    '{
        "location_name_filter": "FOX THEATER",
        "comedy_filter": true,
        "min_comedian_popularity": 0.25,
        "comedy_title_allowlist": ["uncle louie", "variety show"],
        "onboarded_via": "TASK-3242: Fox Theater Salinas is a multi-use Squarespace venue whose own Events page links out to its Ticketor box office tickets831.com (multi-venue homepage JSON-LD). location_name_filter isolates this venue; comedy_filter isolates comedy on the genre-less feed. Confirmed comedy 2026-06-24: Richard Villa (stand-up), The Uncle Louie Variety Show (comedy duo)."
    }'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJN28z2MH4jYARN6RkmvjuQG0' OR c.name = 'Fox Theater Salinas')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'json_ld'
  );
