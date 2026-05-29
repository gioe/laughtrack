-- TASK-2516: Backfill per-club success_rate, which was NULL for every row.
-- The run-summary aggregator never populated scraper_run_clubs.success_rate, so
-- the Grafana "Per-club success-rate trend" panel (and the HTML dashboard's
-- per-club summary) had nothing to chart. Per-club scrapes are a single attempt,
-- so the success signal is binary: 100 when the club scraped without error, 0
-- otherwise. Going forward the aggregator emits the same value at write time.
UPDATE scraper_run_clubs
SET success_rate = CASE WHEN success THEN 100.0 ELSE 0.0 END
WHERE success_rate IS NULL;
