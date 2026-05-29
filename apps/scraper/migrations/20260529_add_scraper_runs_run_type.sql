-- TASK-2518: Distinguish real scraper snapshots from generic pipeline records
-- with an explicit run_type column instead of a fragile run_key naming convention.
--
-- persist_snapshot writes run_type='scraper' (real scrape runs with club rows);
-- persist_pipeline_run writes run_type='pipeline' (generic GitHub Actions jobs
-- with no scraper_run_clubs children). The Scraper Health dashboard and alert
-- rules key off run_type instead of run_key LIKE 'scraper:%'.

ALTER TABLE scraper_runs
    ADD COLUMN IF NOT EXISTS run_type TEXT NOT NULL DEFAULT 'scraper';

-- Backfill: every pre-existing pipeline row carries a run_key of the shape
-- '<pipeline_key>:<run_id>:<attempt>' (never the 'scraper:' prefix).
UPDATE scraper_runs
    SET run_type = 'pipeline'
    WHERE run_key NOT LIKE 'scraper:%'
      AND run_type <> 'pipeline';

CREATE INDEX IF NOT EXISTS idx_scraper_runs_run_type
    ON scraper_runs (run_type, exported_at DESC);
