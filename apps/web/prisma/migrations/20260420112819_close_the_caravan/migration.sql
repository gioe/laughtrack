-- Close The Caravan (club 65)
UPDATE clubs
SET status = 'closed',
    visible = false,
    closed_at = COALESCE(closed_at, '2026-04-20T11:28:19.535452+00:00'::timestamptz)
WHERE id = 65 AND status <> 'closed';
