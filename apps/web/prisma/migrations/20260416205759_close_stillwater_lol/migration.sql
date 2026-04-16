-- Close Stillwater LOL (club 802)
UPDATE clubs
SET status = 'closed',
    visible = false,
    closed_at = COALESCE(closed_at, '2026-04-16T20:57:59.026941+00:00'::timestamptz)
WHERE id = 802 AND status <> 'closed';
