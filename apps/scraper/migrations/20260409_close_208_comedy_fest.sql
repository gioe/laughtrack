-- TASK-1106: Close 208 Comedy Fest (id=836) — defunct festival.
--
-- Investigation findings:
--   - Domain 208comedyfest.com does not resolve (DNS dead)
--   - SeatEngine subdomain (www-208comedyfest-com.seatengine.com) redirects to
--     SeatEngine's marketing homepage — venue page no longer exists
--   - 0 total shows ever scraped, no city/state on record
--   - Related deny entry "Submit to the 208 Comedy Festival Please" already exists
--
-- Action: close and hide the club record. No shows to delete (total_shows=0).

BEGIN;

UPDATE clubs
SET status    = 'closed',
    visible   = false,
    closed_at = NOW()
WHERE id = 836;  -- 208 Comedy Fest

COMMIT;
