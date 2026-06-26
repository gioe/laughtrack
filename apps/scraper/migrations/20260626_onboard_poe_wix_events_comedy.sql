-- TASK-3340: Capture Poe's Magic Theatre (club 565) comedy-cabaret shows via Wix Events.
--
-- Poe's Magic Theatre (poesmagic.com, club 565) and "Poe's Comedy Cabaret"
-- (poescabaret.com) are the SAME operation (Poe's Magic, LLC) at the Lord
-- Baltimore Hotel — poescabaret.com is a marketing site that links to
-- poesmagic.com/events/... for ticketing. They must NOT be onboarded as a
-- separate club (TASK-3294 / objective 9 dedup).
--
-- Coverage gap: club 565's only source was SeatEngine (venue 545), which now
-- returns just 3 stale magic-showcase events. The venue's live calendar has
-- migrated to the site's native Wix Events app (88 events at
-- /_api/wix-one-events-server/web/paginated-events/viewer), which carries the
-- comedy-cabaret programming (e.g. the recurring "Poe's Comedy Brunch") that
-- SeatEngine never exposed. The scrape orchestrator uses fallback semantics
-- (only the lowest-priority enabled source that returns shows contributes), so
-- the SeatEngine source must be retired for the Wix source to run.
--
-- The Wix feed is MIXED-USE (magic showcases, Lord Baltimore ghost tours,
-- drag/burlesque brunches, comedy), so the new source opts into comedy_filter
-- (convention #197 / the mixed-use comedy_filter pattern): only comedy events
-- are persisted. With the filter, "Poe's Comedy Brunch" (and any future
-- stand-up/improv) is kept while the magic/ghost-tour/brunch programming is
-- dropped — appropriate for a comedy-discovery product.
--
-- Idempotent: re-running disables SeatEngine again, and inserts-or-updates the
-- single wix_events priority-0 source.

-- 1. Retire the stale SeatEngine source (keep the row for history).
UPDATE scraping_sources s
   SET enabled = FALSE,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND c.id = 565
   AND s.platform = 'seatengine'::"ScrapingPlatform";

-- 2. Add the Wix Events source as the primary (priority 0), comedy-filtered.
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
    'wix_events'::"ScrapingPlatform",
    'wix_events',
    'https://www.poesmagic.com',
    0,
    TRUE,
    jsonb_build_object(
        'comedy_filter', TRUE,
        'note', 'TASK-3340 mixed-use Wix calendar (magic/ghost-tours/brunch/comedy); comedy_filter keeps only the comedy-cabaret programming, e.g. Poe''s Comedy Brunch. Replaces the stale SeatEngine venue 545 source.'
    )
  FROM clubs c
 WHERE c.id = 565
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.platform = 'wix_events'::"ScrapingPlatform"
   );

UPDATE scraping_sources s
   SET scraper_key = 'wix_events',
       source_url = 'https://www.poesmagic.com',
       priority = 0,
       enabled = TRUE,
       metadata = jsonb_build_object(
           'comedy_filter', TRUE,
           'note', 'TASK-3340 mixed-use Wix calendar (magic/ghost-tours/brunch/comedy); comedy_filter keeps only the comedy-cabaret programming, e.g. Poe''s Comedy Brunch. Replaces the stale SeatEngine venue 545 source.'
       ),
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND c.id = 565
   AND s.platform = 'wix_events'::"ScrapingPlatform";
