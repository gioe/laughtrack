-- TASK-3522: Guard — keep show-routing Eventbrite organizer feed-clubs visible=false.
--
-- Decision (TASK-3519, option c; convention #295): the per-event venue club is the
-- canonical home for an Eventbrite organizer feed's routed shows. An organizer
-- feed-club (scraping_sources.source_url contains eventbrite.com/o/) whose feed routes
-- 100% of its shows to DISTINCT per-event venue clubs should NOT also surface in browse,
-- so it is set visible=false. Web browse (findClubsWithCount.tsx) already requires
-- visible=true AND an upcoming show, so a visible-but-show-routing organizer club only
-- ever renders an empty state on a direct /club/<slug> URL.
--
-- WHY a num_shows threshold (not just "0 own shows"):
--   In organizer mode the scraper routes each event to its own per-venue club (conv #292),
--   and these organizer feed-clubs are wired as a bare scraping_sources row on a real club
--   WITHOUT a production_company, so NOTHING in the DB durably links the organizer club to
--   the venue clubs its feed routes to (shows.scraped_by_organizer_id is NULL on that path,
--   eventbrite_organizer_venues is not written). That means "0 own upcoming shows" alone
--   CANNOT distinguish a true router from a genuine venue whose own feed is simply empty
--   right now — both look identical in clubs/shows.
--
--   The only durable "feed is active and routing elsewhere" signal is scraper telemetry:
--   scraper_run_clubs.num_shows records how many shows the organizer feed produced on a run
--   (attributed to the parent organizer entity, conv #294), even when those shows land on
--   OTHER clubs. So a true router = an organizer feed-club with 0 own upcoming shows whose
--   feed still recently produced shows (num_shows high). A genuine-but-empty venue produces
--   ~0 shows. Production audit (2026-06-29) shows a wide, clean gap between the two
--   populations:
--       confirmed routers (already hidden): 28..250 shows produced, 0 own upcoming
--           The Spotlight Comedy (11081)=250, Gold Coast Comedy Club (11449)=60,
--           The Comedy Bar - Pittsburgh (8708)=42, BATS Improv (11133)=36,
--           Henceforth Comedy (8694)=32, Comedy Oakland (11089)=28
--       genuine low-volume venues (kept visible): <= 2 shows produced, 0 own upcoming
--           Comedy on Collins (200), The Drop Comedy Club (9065), Pagliacci's (8701),
--           Lots of Laughs (10950), Chatterbox (8855), Martinez Campbell Theater (11104),
--           Clayton Club Saloon (11105), Bobby's Place (10951), McCues (10959),
--           Blend Comedy (10960), Deja Blue (11119), Music City Starfactory (11121),
--           CBA Event Center (11251)
--   A threshold of num_shows >= 10 over the trailing 30 days sits squarely in that gap:
--   it catches every confirmed high-volume router and never touches a genuine venue. Cases
--   in the ambiguous 1..9 band are intentionally left for human review (criterion is
--   manual) rather than auto-hidden — a near-dead genuine venue must not be hidden by
--   mistake.
--
-- CURRENT STATE: running the guard below today affects 0 rows — every high-volume router is
-- already visible=false (Comedy Oakland 11089, Gold Coast 11449, The Spotlight 11081,
-- The Comedy Bar - Pittsburgh 8708, BATS 11133, Henceforth 8694). This migration therefore
-- asserts the invariant at deploy time and is the canonical, re-runnable audit for future
-- onboards. After onboarding any eventbrite /o/ organizer feed, re-run the AUDIT query
-- below; if it returns rows, those organizer clubs are routing elsewhere and should be
-- hidden (re-run the UPDATE, or hide them by id).
--
-- ============================================================================
-- AUDIT (re-runnable; copy into `make query SQL="..."`): organizer feed-clubs that are
-- still visible but route their (recent) shows entirely to distinct venue clubs.
-- ----------------------------------------------------------------------------
--   SELECT c.id, c.name, c.visible,
--          (SELECT COALESCE(MAX(src.num_shows), 0)
--             FROM scraper_run_clubs src
--            WHERE src.club_id = c.id
--              AND src.created_at > NOW() - INTERVAL '30 days') AS max_feed_30d
--     FROM clubs c
--    WHERE c.visible = true
--      AND c.status = 'active'
--      AND EXISTS (SELECT 1 FROM scraping_sources ss
--                   WHERE ss.club_id = c.id
--                     AND ss.platform = 'eventbrite'
--                     AND ss.enabled = true
--                     AND ss.source_url LIKE '%eventbrite.com/o/%')
--      AND NOT EXISTS (SELECT 1 FROM shows s
--                       WHERE s.club_id = c.id AND s.date > NOW())
--      AND (SELECT COALESCE(MAX(src.num_shows), 0)
--             FROM scraper_run_clubs src
--            WHERE src.club_id = c.id
--              AND src.created_at > NOW() - INTERVAL '30 days') >= 10
--    ORDER BY max_feed_30d DESC;
-- ============================================================================

BEGIN;

-- Guard: hide any currently-visible organizer feed-club that produces shows via its
-- eventbrite /o/ feed but routes them all to distinct venue clubs (0 own upcoming shows,
-- >= 10 shows produced in the trailing 30 days). Idempotent: affects 0 rows when every
-- such router is already hidden.
UPDATE clubs c
SET visible = false
WHERE c.visible = true
  AND c.status = 'active'
  AND EXISTS (
        SELECT 1 FROM scraping_sources ss
         WHERE ss.club_id = c.id
           AND ss.platform = 'eventbrite'
           AND ss.enabled = true
           AND ss.source_url LIKE '%eventbrite.com/o/%'
      )
  AND NOT EXISTS (
        SELECT 1 FROM shows s
         WHERE s.club_id = c.id AND s.date > NOW()
      )
  AND (
        SELECT COALESCE(MAX(src.num_shows), 0)
          FROM scraper_run_clubs src
         WHERE src.club_id = c.id
           AND src.created_at > NOW() - INTERVAL '30 days'
      ) >= 10;

COMMIT;
