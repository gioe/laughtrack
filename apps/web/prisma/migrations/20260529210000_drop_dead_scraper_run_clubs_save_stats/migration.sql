-- TASK-2517: Drop the dead per-club save-stat columns from scraper_run_clubs.
--
-- These seven columns were NULL for every row: the DB save is computed in bulk
-- at the run level and never attributed per club, so PerClubStat leaves them None
-- and they persist as NULL. The run-level scraper_runs table already carries the
-- populated totals. The only reader (apps/web/lib/admin/pipelines.ts shows_saved)
-- fetched but never rendered it and is removed in the same change. success_rate
-- is retained (populated by TASK-2516, charted by Grafana + the HTML dashboard).
--
-- This is the prod-facing copy of apps/scraper/migrations/
-- 20260529_drop_dead_scraper_run_clubs_save_stats.sql. IF EXISTS keeps it a no-op
-- if the scraper migration runner dropped the columns first.
ALTER TABLE scraper_run_clubs
    DROP COLUMN IF EXISTS shows_saved,
    DROP COLUMN IF EXISTS shows_inserted,
    DROP COLUMN IF EXISTS shows_updated,
    DROP COLUMN IF EXISTS shows_failed_save,
    DROP COLUMN IF EXISTS shows_skipped_dedup,
    DROP COLUMN IF EXISTS shows_validation_failed,
    DROP COLUMN IF EXISTS shows_db_errors;
