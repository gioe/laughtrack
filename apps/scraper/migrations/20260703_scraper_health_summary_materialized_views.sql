-- TASK-3573: Precompute scraper-health regression summaries for Grafana.
--
-- The scraper-health alert rules (apps/web/monitoring/grafana/scraper-health-alerts.yaml)
-- recompute last-two-run and 30-day club-history comparisons on EVERY Grafana evaluation
-- (hourly), each scan hitting scraper_runs + scraper_run_clubs. The underlying data only
-- changes once per nightly scrape, so 23 of every 24 evaluations rescan the same rows to
-- produce the same answer.
--
-- These materialized views precompute exactly those comparisons. The scraper REFRESHes
-- them once, at the end of each full 'scraper' run (PostgresMetricsRepository.
-- refresh_health_summary), so Grafana reads a handful of already-computed rows instead of
-- re-running the CTEs. Because the view definitions are byte-for-byte the CTE bodies the
-- rules used to embed, the regression semantics are preserved: an alert only ever changes
-- state when a new run lands, which is exactly when a refresh happens.
--
-- Deliberately NOT precomputed: the pipeline-staleness rule (rule 5). It measures
-- NOW() - MAX(exported_at), which must be evaluated live (a frozen "hours_stale" would
-- never grow between runs) and is already a single cheap MAX on scraper_runs — nothing to
-- amortize. It stays an inline rawSql query.
--
-- Idempotent: CREATE MATERIALIZED VIEW IF NOT EXISTS + additive GRANTs. Created WITH DATA
-- so the views are populated from existing history the moment this migration applies.

BEGIN;

-- ---------------------------------------------------------------------------
-- Overall scalars: success-rate drop (rule 1) and error-count spike (rule 3),
-- both baselined against the trailing-7-run rolling average (rn BETWEEN 2 AND 8)
-- of the latest 8 real 'scraper' runs. Always yields exactly one row.
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_scraper_health_overall AS
WITH ranked AS (
    SELECT success_rate,
           ROW_NUMBER() OVER (ORDER BY exported_at DESC) AS rn
    FROM scraper_runs
    WHERE run_type = 'scraper'
),
errors_per_run AS (
    SELECT r.id, r.exported_at, COUNT(e.id) AS errors
    FROM scraper_runs r
    LEFT JOIN scraper_run_errors e ON e.run_id = r.id
    WHERE r.run_type = 'scraper'
    GROUP BY r.id, r.exported_at
),
errors_ranked AS (
    SELECT errors,
           ROW_NUMBER() OVER (ORDER BY exported_at DESC) AS rn
    FROM errors_per_run
)
SELECT
    (SELECT COALESCE(AVG(success_rate) FILTER (WHERE rn BETWEEN 2 AND 8), 0)
          - COALESCE(MAX(success_rate) FILTER (WHERE rn = 1), 0)
       FROM ranked
      WHERE rn <= 8) AS success_rate_drop,
    (SELECT COALESCE(MAX(errors) FILTER (WHERE rn = 1), 0)
          - COALESCE(AVG(errors) FILTER (WHERE rn BETWEEN 2 AND 8), 0)
       FROM errors_ranked
      WHERE rn <= 8) AS error_spike
WITH DATA;

-- ---------------------------------------------------------------------------
-- Rule 2: clubs that returned shows in the previous run but zero in the latest.
-- Matches the prev>0 -> latest=0 transition, so a club appears for exactly one
-- run (on the next run its "previous" is itself 0 and it drops out) — same
-- fire-once semantics the inline rule had. club_shows SUMs per (run_id,
-- club_name) because scraper_run_clubs has no UNIQUE on (run_id, club_name).
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_scraper_health_dropped_to_zero AS
WITH last_two AS (
    SELECT id,
           ROW_NUMBER() OVER (ORDER BY exported_at DESC) AS rn
    FROM scraper_runs
    WHERE run_type = 'scraper'
),
club_shows AS (
    SELECT c.run_id, c.club_name, SUM(c.num_shows) AS num_shows
    FROM scraper_run_clubs c
    JOIN last_two ON last_two.id = c.run_id
    GROUP BY c.run_id, c.club_name
)
SELECT latest.club_name AS club,
       1 AS dropped_to_zero
FROM club_shows latest
JOIN last_two lt_latest ON lt_latest.id = latest.run_id AND lt_latest.rn = 1
JOIN club_shows prev ON prev.club_name = latest.club_name
JOIN last_two lt_prev ON lt_prev.id = prev.run_id AND lt_prev.rn = 2
WHERE latest.num_shows = 0
  AND prev.num_shows > 0
WITH DATA;

-- ---------------------------------------------------------------------------
-- Rule 2b/4: self-healing companion — clubs at zero shows for the last 2
-- consecutive FULL runs (clubs_processed > 1 keeps single-club verify runs out
-- of the rn=1/rn=2 window) that still had shows within the trailing 30 days.
-- The 30-day history lookback includes verify runs (run_type IN
-- ('scraper','verify')): any recent run proving the club had shows is evidence
-- it is not a legitimately dark venue. The NOW() anchor is baked at REFRESH
-- time (i.e. anchored to the latest run's wall-clock), which tracks the daily
-- run cadence — functionally identical to the inline rule's eval-time anchor.
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_scraper_health_consecutive_zero AS
WITH full_runs AS (
    SELECT id, exported_at,
           ROW_NUMBER() OVER (ORDER BY exported_at DESC) AS rn
    FROM scraper_runs
    WHERE run_type = 'scraper'
      AND clubs_processed > 1
),
club_shows AS (
    SELECT c.run_id, c.club_name, SUM(c.num_shows) AS num_shows
    FROM scraper_run_clubs c
    JOIN full_runs fr ON fr.id = c.run_id AND fr.rn <= 2
    GROUP BY c.run_id, c.club_name
),
history AS (
    SELECT c.club_name, MAX(c.num_shows) AS max_shows_30d
    FROM scraper_run_clubs c
    JOIN scraper_runs r ON r.id = c.run_id
    WHERE r.run_type IN ('scraper', 'verify')
      AND r.exported_at >= NOW() - INTERVAL '30 days'
    GROUP BY c.club_name
)
SELECT latest.club_name AS club,
       1 AS consecutive_zero
FROM club_shows latest
JOIN full_runs lt_latest ON lt_latest.id = latest.run_id AND lt_latest.rn = 1
JOIN club_shows prev ON prev.club_name = latest.club_name
JOIN full_runs lt_prev ON lt_prev.id = prev.run_id AND lt_prev.rn = 2
JOIN history h ON h.club_name = latest.club_name
WHERE latest.num_shows = 0
  AND prev.num_shows = 0
  AND h.max_shows_30d > 0
WITH DATA;

-- Grafana's read-only role reads the precomputed views instead of the base
-- tables. GRANT ... ON ALL TABLES does NOT cover materialized views, so each
-- view must be granted by name (kept in sync with
-- apps/web/prisma/scripts/create_grafana_readonly_role.sql). Guarded so the
-- migration still applies on databases (local/dev) where grafana_ro is absent.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grafana_ro') THEN
        GRANT SELECT ON
            public.mv_scraper_health_overall,
            public.mv_scraper_health_dropped_to_zero,
            public.mv_scraper_health_consecutive_zero
            TO grafana_ro;
    END IF;
END $$;

COMMIT;
