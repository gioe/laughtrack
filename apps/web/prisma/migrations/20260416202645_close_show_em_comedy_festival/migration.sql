-- Close Show Em Comedy Festival (club 795)
UPDATE clubs
SET status = 'closed',
    visible = false,
    closed_at = COALESCE(closed_at, '2026-04-16T20:26:45.307966+00:00'::timestamptz)
WHERE id = 795 AND status <> 'closed';
