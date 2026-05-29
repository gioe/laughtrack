-- TASK-2517: Drop the dead per-club save-stat columns from scraper_run_clubs.
--
-- DECISION: drop, not populate.
-- These seven columns were NULL for every row (verified 26/26). Root cause: the
-- DB save (DatabaseOperationResult) is computed in bulk at the run level and is
-- never attributed back to individual clubs, so MetricsAggregator builds each
-- PerClubStat with these fields left as None and they persist as NULL. Populating
-- them would require re-plumbing the save path to attribute every insert/update
-- to its originating club — disproportionate for a low-value diagnostic, and the
-- run-level scraper_runs table already carries these same totals (which ARE
-- populated and consumed). The only reader of any of these per-club columns was
-- apps/web/lib/admin/pipelines.ts (shows_saved), which fetched it into
-- AdminPipelineClubStat.showsSaved but never rendered it. Dropping here; the
-- web-side read and the matching prisma migration are removed in the same change.
--
-- success_rate is intentionally retained (TASK-2516 populates it and Grafana +
-- the HTML dashboard chart it). Idempotent so it is a no-op if the sibling
-- prisma migration already dropped the columns in prod.
ALTER TABLE scraper_run_clubs
    DROP COLUMN IF EXISTS shows_saved,
    DROP COLUMN IF EXISTS shows_inserted,
    DROP COLUMN IF EXISTS shows_updated,
    DROP COLUMN IF EXISTS shows_failed_save,
    DROP COLUMN IF EXISTS shows_skipped_dedup,
    DROP COLUMN IF EXISTS shows_validation_failed,
    DROP COLUMN IF EXISTS shows_db_errors;
