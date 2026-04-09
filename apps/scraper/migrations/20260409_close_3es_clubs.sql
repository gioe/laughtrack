-- TASK-1107: Close 3E's (id=553) and Demo - 3E's Comedy Club (id=433).
--
-- Investigation findings:
--   - Club 553 "3E's": no website, no city/state, no scraping URL,
--     SeatEngine venue 533 returns 404 on all endpoints, 0 shows ever
--   - Club 433 "Demo - 3E's Comedy Club": SeatEngine demo venue (id=408),
--     API returns 404, subdomain shows only a SeatEngine demo page, 0 shows ever
--   - Both are defunct SeatEngine bulk-import entries with no comedy content
--
-- Action: close and hide both club records. No shows to delete (total_shows=0).

BEGIN;

UPDATE clubs
SET status    = 'closed',
    visible   = false,
    closed_at = NOW()
WHERE id IN (553, 433);  -- 3E's, Demo - 3E's Comedy Club

COMMIT;
