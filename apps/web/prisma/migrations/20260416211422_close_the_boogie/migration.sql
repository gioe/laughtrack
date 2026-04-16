-- Close The Boogie (club 788)
UPDATE clubs
SET status = 'closed',
    visible = false,
    closed_at = COALESCE(closed_at, '2026-04-16T21:14:22.506620+00:00'::timestamptz)
WHERE id = 788 AND status <> 'closed';
