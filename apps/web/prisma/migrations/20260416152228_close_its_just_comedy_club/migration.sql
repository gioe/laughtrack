-- Close It's just comedy club (club 846)
-- Website domain parked, SeatEngine API 404 (venue 289), no ticketed shows
-- Only active presence is an open mic signup on Slotted.co (not a ticketed venue)
UPDATE clubs SET visible = false, status = 'closed', closed_at = NOW() WHERE id = 846;
