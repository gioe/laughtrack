-- TASK-2052: Delete orphan ticketless Tampa Funny Bone shows.
--
-- These six rows are stale pre-etix-migration exhaust from the former
-- live_nation scraper path. They are past shows, have no tickets, and cannot be
-- reconciled by the current etix scraper because the public listing no longer
-- exposes these past dates.
--
-- Dependent ticket, lineup_items, tagged_shows, and sent_notifications rows
-- cascade from shows per schema.prisma.

BEGIN;

DELETE FROM shows
WHERE club_id = 1053
  AND id IN (
    916941,
    916942,
    916945,
    916946,
    916948,
    916974
  );

COMMIT;
