-- Close Laughing Gas Comedy Club (club 830)
-- Venue is defunct — bulk-imported from SeatEngine on 2026-04-06, never returned shows
-- Yelp lists BOTH locations as CLOSED:
--   - Cape Girardeau MO (2106 William St) — closed as of December 2025
--   - Winston-Salem NC (2105 Peters Creek Pkwy) — closed as of October 2024
-- Website laughinggascomedyclub.com is a parked domain (redirects to /lander)
-- SeatEngine API returns 404 for stored venue ID 271
-- SeatEngine subdomain www-laughingas-net.seatengine.com redirects to seatengine.com home (account deactivated)
UPDATE clubs SET visible = false, status = 'closed', closed_at = NOW() WHERE id = 830;
