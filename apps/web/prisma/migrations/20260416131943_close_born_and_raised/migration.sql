-- Close Born & Raised (club 792) — defunct SeatEngine venue
-- Website (bornandraisednw.com) is down, SeatEngine venue ID 210 returns 404,
-- no web presence found. Bulk-imported 2026-04-06, never returned shows.
UPDATE clubs
SET status = 'closed',
    closed_at = NOW()
WHERE id = 792;
