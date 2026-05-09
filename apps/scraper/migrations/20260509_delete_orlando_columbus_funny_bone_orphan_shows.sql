-- TASK-2049: Delete orphan ticketless Orlando + Columbus Funny Bone shows.
--
-- These 19 rows (17 at Orlando club_id=1027, 2 at Columbus club_id=308) are
-- stale exhaust from the original `funny_bone` Rockhouse Partners WordPress
-- scraper (introduced TASK-1008, removed TASK-1477 on 2026-04-15 — the exact
-- last_scraped_date on every row). After TASK-1669 migrated the Funny Bone
-- chain off DataDome-blocked Etix to Ticketmaster (live_nation), the
-- *.funnybone.com/event/<slug>/<venue-slug> URL pattern these rows reference is
-- no longer produced by any active scraper, so they cannot be reconciled and
-- have been invisible (UI gates show visibility on tickets.length>0).
--
-- TASK-2032 audit confirmed the current live_nation/Ticketmaster Discovery API
-- path emits tickets for 100% of returned events at both venues, so the
-- show_page_url pattern guard cleanly excludes any legitimate live_nation rows.
--
-- Dependent ticket, lineup_items, tagged_shows, and sent_notifications rows
-- cascade from shows per schema.prisma.

BEGIN;

DELETE FROM shows
WHERE club_id IN (308, 1027)
  AND id IN (
    -- Columbus Funny Bone (club_id=308)
    974303,
    974351,
    -- Orlando Funny Bone (club_id=1027)
    836399,
    836410,
    836413,
    836420,
    836424,
    836427,
    836432,
    897992,
    898003,
    898007,
    898013,
    898018,
    898020,
    898027,
    898060,
    1032242,
    1032290
  );

COMMIT;
