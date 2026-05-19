-- Clean stale scraping_sources rows ahead of enforcing the scrapeability
-- invariant:
--   * visible active clubs should have at least one enabled scraping source
--   * hidden / non-active clubs should have no scraping source rows
--   * disabled scraping_sources rows are stale relationship state and should
--     not be retained as audit history
--
-- Context:
-- TASK-1950 disabled several no-event SeatEngine sources and left five clubs
-- visible+active with no enabled source:
--   82   Wicked Funny Comedy Club North Andover
--   521  The Royal Comedy Theatre
--   568  The Brick Room
--   589  Midtown Comedy Lounge
--   1438 The Comedy Scene
--
-- Those five require source investigation before they can be hidden or restored.
-- This migration therefore leaves disabled-only visible+active clubs untouched.
-- It only removes rows already attached to hidden / non-active clubs, plus
-- disabled fallback rows on visible+active clubs that already have another
-- enabled source. The durable audit trail is this migration and the linked
-- tasks, not stale rows in scraping_sources.metadata.

DELETE FROM scraping_sources ss
USING clubs c
WHERE c.id = ss.club_id
  AND (
      c.visible IS DISTINCT FROM true
      OR c.status <> 'active'
      OR (
          ss.enabled = false
          AND EXISTS (
              SELECT 1
              FROM scraping_sources enabled_source
              WHERE enabled_source.club_id = ss.club_id
                AND enabled_source.enabled = true
          )
      )
  );
