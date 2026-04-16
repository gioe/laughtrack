-- Close Hu Ke Lau (club 828) — permanently closed April 2018, building demolished,
-- Yelp CLOSED, SeatEngine API 404, Chicopee MA
UPDATE clubs
SET visible = false,
    status = 'closed',
    closed_at = NOW()
WHERE id = 828;
