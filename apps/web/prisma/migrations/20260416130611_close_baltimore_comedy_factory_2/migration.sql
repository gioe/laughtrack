-- Close Baltimore Comedy Factory 2 (club 845)
-- Defunct SeatEngine sub-venue; main Baltimore Comedy Factory is club 86.
-- Website (2.baltimorecomedyfactory.com) does not resolve; SeatEngine venue 288 returns 404.
UPDATE clubs SET visible = false, status = 'closed', closed_at = now() WHERE id = 845;
