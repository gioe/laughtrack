-- Close Southwest Florida Event Center (club 800)
UPDATE clubs
SET status = 'closed',
    visible = false,
    closed_at = COALESCE(closed_at, '2026-04-16T20:48:00.523154+00:00'::timestamptz)
WHERE id = 800 AND status <> 'closed';
