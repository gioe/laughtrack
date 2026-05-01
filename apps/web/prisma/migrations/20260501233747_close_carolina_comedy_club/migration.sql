-- Close Carolina Comedy Club (club 329)
UPDATE clubs
SET status = 'closed',
    visible = false,
    closed_at = COALESCE(closed_at, '2026-05-01T23:37:47.574778+00:00'::timestamptz)
WHERE id = 329 AND status <> 'closed';
