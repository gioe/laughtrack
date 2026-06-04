-- Add comedians.visible as a soft-suppression flag mirroring clubs.visible
-- (see docs/comedian-visible-consolidation.md). The migration is split into
-- three steps that share one transaction so the snapshot, the column add, and
-- the backfill cannot land separately:
--
--   1. ALTER TABLE comedians ADD COLUMN visible BOOLEAN DEFAULT true,
--      plus an index on (visible) for the per-query WHERE visible = true
--      predicate that downstream tasks (TASK-2639) will add.
--
--   2. Snapshot the entire current comedian_deny_list into
--      comedian_deny_list_archive_pre_consolidation. The snapshot is the
--      rollback substrate (it lets us restore the deny-list verbatim) and
--      the audit trail (it preserves reason/added_by/deleted_at for the
--      deny-list rows that step 3 promotes-and-removes).
--
--   3. Backfill: for every deny-list row whose normalized name matches an
--      existing comedians row, set that comedians row to visible=false and
--      remove the deny-list row. The orphan deny-list rows (~1,642 with no
--      matching comedian) are deliberately left in place per ADR Decision 1:
--      they continue to function as pre-emptive name blocks for names that
--      have never been ingested.
--
-- The UPDATE and DELETE share one CTE chain (the `matched` CTE) so they
-- consume the same set of name pairs. Splitting them into two statements
-- would put `matched` out of scope for the DELETE.

-- 1. Column and index.
ALTER TABLE "comedians" ADD COLUMN "visible" BOOLEAN DEFAULT true;

CREATE INDEX "comedians_visible_idx" ON "comedians"("visible");

-- 2. Snapshot the deny-list. The archive table is the rollback substrate
-- and the audit trail; application code does not read it. A future chore
-- can drop it once the consolidation has soaked in production.
CREATE TABLE "comedian_deny_list_archive_pre_consolidation" AS
SELECT *, now() AS archived_at
FROM "comedian_deny_list";

-- 3. Promote-and-remove. The normalized-name JOIN mirrors the expression the
-- scraper handler uses to match deny-list names against comedian names
-- (apps/scraper/src/laughtrack/core/entities/comedian/handler.py
-- _normalize_deny_list_name). With ~50k comedians and ~1,990 deny-list rows,
-- this is a one-shot sequential expression match; the ADR notes that a
-- temporary functional index can be added if measured runtime is excessive.
WITH matched AS (
    SELECT c.id   AS comedian_id,
           d.name AS deny_name
    FROM   comedian_deny_list d
    JOIN   comedians c
      ON lower(btrim(regexp_replace(replace(c.name, chr(160), ' '),
                                    '[[:space:]]+', ' ', 'g')))
       = lower(btrim(regexp_replace(replace(d.name, chr(160), ' '),
                                    '[[:space:]]+', ' ', 'g')))
),
promoted AS (
    UPDATE comedians
       SET visible = false
     WHERE id IN (SELECT comedian_id FROM matched)
    RETURNING id
)
DELETE FROM comedian_deny_list
WHERE name IN (SELECT deny_name FROM matched);
