-- Close Morty's Comedy Joint (id=816, Indianapolis, IN)
-- Yelp lists CLOSED as of January 2026 (last updated 2026-01)
-- SeatEngine API /api/v1/venues/247 returns 404
-- mortys.seatengine.net returns 404 (subdomain deactivated)
-- www.mortyscomedy.com redirects to bare www.seatengine.com (account deactivated)
-- Previously at 3824 E 82nd St, Indianapolis, IN

UPDATE clubs
SET status = 'closed',
    visible = false,
    closed_at = NOW()
WHERE id = 816;
