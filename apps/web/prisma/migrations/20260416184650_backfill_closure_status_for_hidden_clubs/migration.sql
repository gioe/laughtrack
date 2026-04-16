-- Backfill closure status for clubs hidden under the old /hide-club flow.
-- Before TASK-1534, /hide-club set visible=false but left status='active' and closed_at=NULL,
-- while the convention for confirmed-defunct venues (now handled by /close-club) is to set
-- status='closed' + closed_at=NOW(). These rows were already patched in the live DB;
-- this migration is a no-op there, but it's required for deterministic rebuilds.
--
-- Covers:
--   798 — Jester's Comedy Club       (TASK-1512)
--   830 — Laughing Gas Comedy Club   (TASK-1514)
--   831 — Johnny & June's            (TASK-1513)

UPDATE clubs
SET status = 'closed',
    closed_at = COALESCE(closed_at, NOW())
WHERE id IN (798, 830, 831)
  AND status <> 'closed';
