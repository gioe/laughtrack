-- Close Johnny & June's (club 831)
-- Venue is defunct — bulk-imported from SeatEngine on 2026-04-06, never returned shows
-- Yelp listing marked CLOSED as of November 2025
-- Previously located at 2105 Peters Creek Parkway, Winston-Salem, NC
-- Original domain johnnynjunes.com has been taken over by a Japanese rental property management squatter site
-- SeatEngine API returns 404 for stored venue ID 272
-- SeatEngine subdomain johnnynjunes.seatengine.com redirects to seatengine.com home (account deactivated)
UPDATE clubs SET visible = false, status = 'closed', closed_at = NOW() WHERE id = 831;
