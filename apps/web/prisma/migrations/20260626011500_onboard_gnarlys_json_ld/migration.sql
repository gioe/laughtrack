-- Onboard Gnarly's (Golden, CO) via the existing json_ld scraper - TASK-3406.
--
-- Gnarly's (gnarlys-theater.com) is a 107-seat live-entertainment theater + bar +
-- retro arcade at 1224 Washington Ave Ste 200, Golden, CO 80401. Its own marketing
-- site is a Squarespace/Wix-style shell; all ticketing + the upcoming-events calendar
-- run on its dedicated single-venue Ticketor (ticketor.com) box office at
-- https://www.ticketor.com/gnarlys. The Ticketor /tickets listing page server-renders
-- one schema.org Event JSON-LD block per upcoming event (name + startDate + endDate +
-- location + description), so the generic json_ld scraper reads it with a plain static
-- fetch (no force_js_rendering needed — same as Fox Theater Salinas / tickets831.com,
-- migration 20260624070143).
--
-- Confirmed comedy at this venue (verified 2026-06-26 via the live Ticketor JSON-LD):
--   * "Mo Alexander" 2026-07-17 — desc "nationally touring comedian ... night of big
--     laughs" (stand-up).
--   * "Eleazar and Friends" 2026-07-04 — desc "Live Comedy Recording ... Eleazar Guzman
--     & Friends, all seen on Kill Tony" (stand-up).
--   (Professor Phelyx Comedy/Mind-Reading ran 2026-06-13.) Alongside heavy NON-comedy
--   programming: magic matinees, pro wrestling (Red White & Bruised), and burlesque/
--   aerial shows (Heavens Gay-te, Gold Dust & Dirty Secrets).
--
-- Because the venue is MIXED-USE and Ticketor JSON-LD carries no genre/category,
-- metadata.comedy_filter=true isolates comedy via the shared select_comedy_titles
-- heuristic (keyword OR allowlist OR a known comedian above min_comedian_popularity).
-- The two confirmed comedy shows match the comedy keyword regex on their description
-- ("comedy" / "comedian"), so they survive on keyword alone; magic ("laughter" is not a
-- keyword), wrestling, and burlesque are dropped. A future touring comedian above the
-- popularity floor auto-populates with no further config. NO location_name_filter is
-- needed: ticketor.com/gnarlys is Gnarly's OWN single-venue box office (unlike the
-- multi-venue tickets831.com), so every event on the page is this venue's.
--
-- Fixed venue (the club is its own room) -> visible=TRUE.
-- Idempotent: guarded by NOT EXISTS on google_place_id / name (clubs) and
-- (club_id, scraper_key) (scraping_sources), so re-runs and fresh DBs converge.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Gnarly''s', '1224 Washington Ave Ste 200, Golden, CO 80401, USA',
    'http://www.gnarlys-theater.com/',
    'Golden', 'CO', '80401', 'America/Denver', 'US', 'club',
    'ChIJW0ua3Eiba4cRMRmJmtD3pcA', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJW0ua3Eiba4cRMRmJmtD3pcA'
       OR name = 'Gnarly''s'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'json_ld',
    'https://www.ticketor.com/gnarlys/tickets',
    TRUE,
    0,
    '{
        "comedy_filter": true,
        "onboarded_via": "TASK-3406: Gnarly''s (Golden, CO) is a mixed-use entertainment theater whose calendar + tickets run on its dedicated single-venue Ticketor box office (ticketor.com/gnarlys). The /tickets page server-renders schema.org Event JSON-LD per show; the generic json_ld scraper reads it statically. comedy_filter isolates comedy on the genre-less feed. Confirmed comedy 2026-06-26: Mo Alexander (stand-up, 2026-07-17), Eleazar and Friends (stand-up, 2026-07-04)."
    }'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJW0ua3Eiba4cRMRmJmtD3pcA' OR c.name = 'Gnarly''s')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'json_ld'
  );
