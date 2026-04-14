-- Close dormant sub-venue "Secret Baltimore Comedy Factory" (club 271)
-- 0 total shows, no address, no timezone, SeatEngine venue 68 returns 404.
-- The real venue is club 86 (Baltimore Comedy Factory).
UPDATE "Club"
SET "status" = 'closed',
    "closed_at" = NOW()
WHERE "id" = 271;
