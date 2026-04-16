-- Close Gulf Coast Comedy (club 835)
-- Not a physical venue — comedy production/event company that organizes shows at other locations.
-- Website (gulfcoastcomedy.com) is down, SeatEngine API returns 404, never returned shows.
UPDATE clubs SET visible = false, status = 'closed', closed_at = NOW() WHERE id = 835;
