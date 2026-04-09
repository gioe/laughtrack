-- TASK-1108: Close AC Jokes (id=412).
--
-- Investigation findings:
--   - SeatEngine venue 387 returns 404 on all API endpoints
--   - SeatEngine page loads (HTML shell, logo, nav) but calendar and events
--     pages show 0 events
--   - acjokes.com exists on Wix but Wix events API returns 404
--   - No city/state set, 0 shows ever in DB, total_shows=0
--   - Appears to be a defunct SeatEngine bulk-import venue with no real content
--
-- Action: close and hide. No shows to delete (total_shows=0).

BEGIN;

UPDATE clubs
SET status    = 'closed',
    visible   = false,
    closed_at = NOW()
WHERE id = 412;  -- AC Jokes

COMMIT;
