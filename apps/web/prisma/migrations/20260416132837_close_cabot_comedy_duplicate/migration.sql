-- Close Cabot Comedy (club 799) — duplicate of Off Cabot Comedy and Events (club 1351).
-- Club 799 was bulk-imported from SeatEngine (id 221) but the venue is already
-- onboarded as club 1351 with the off_cabot scraper. SeatEngine API returns 401
-- and cabotcomedy.com is down (ECONNREFUSED).
UPDATE clubs
SET visible = false,
    status = 'closed',
    closed_at = NOW()
WHERE id = 799;
