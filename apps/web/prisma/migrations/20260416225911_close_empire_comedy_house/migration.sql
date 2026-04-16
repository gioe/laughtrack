-- Close Empire Comedy House (club 1209)
UPDATE clubs
SET status = 'closed',
    visible = false,
    closed_at = COALESCE(closed_at, '2026-04-16T22:59:11.093740+00:00'::timestamptz)
WHERE id = 1209 AND status <> 'closed';
