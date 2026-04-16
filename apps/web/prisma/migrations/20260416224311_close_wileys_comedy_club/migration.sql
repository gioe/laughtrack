-- Close Wiley's Comedy Club (club 815)
UPDATE clubs
SET status = 'closed',
    visible = false,
    closed_at = COALESCE(closed_at, '2026-04-16T22:43:11.813863+00:00'::timestamptz)
WHERE id = 815 AND status <> 'closed';
