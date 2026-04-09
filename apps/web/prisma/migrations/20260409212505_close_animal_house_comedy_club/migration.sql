-- Close Animal House Comedy Club (club 351)
-- Website down (ECONNREFUSED), SeatEngine subdomain redirects to seatengine.com (302),
-- SeatEngine API returns 404, no upcoming shows found online, no active web presence.
UPDATE "clubs"
SET visible = false
WHERE id = 351;
