-- TASK-715: Deactivate Capitol Hill Comedy Bar (id=94) — duplicate of Emerald City Comedy Club (id=106).
--
-- Investigation findings:
--   - Both clubs share the same physical address: 210 Broadway E, Seattle WA 98102
--   - Both share seatengine_id=588 (Emerald City's SeatEngine venue)
--   - Capitol Hill's scraping_url (comedyslashbar.com/events) HTTP 302-redirects to
--     www.emeraldcitycomedy.com/events (Emerald City, id=106)
--   - "Capitol Hill Comedy Bar" was the venue's former name; it rebranded to Emerald City Comedy Club
--
-- Result: id=94 is an alias/stale record for the same physical venue as id=106.
-- Action: close id=94, delete its 59 duplicate shows (65 lineup_items cascade).

BEGIN;

-- 1. Close the duplicate club record and hide it from the web app.
UPDATE clubs
SET status    = 'closed',
    visible   = false
WHERE id = 94;  -- Capitol Hill Comedy Bar

-- 2. Delete duplicate shows (and their lineup_items via ON DELETE CASCADE).
--    These shows were scraped from the same SeatEngine venue as id=106 due to the redirect.
DELETE FROM shows WHERE club_id = 94;

COMMIT;
