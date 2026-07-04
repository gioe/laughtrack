-- TASK-2834: Make the club-level scraper-health alerts actionable in Discord.
--
-- Recreates the two club-level materialized views from
-- 20260703_scraper_health_summary_materialized_views.sql with two changes:
--
-- 1. club_id label — each row now carries the club's scraper_run_clubs.club_id
--    (as text, so Grafana treats it as a label, not a value). The Discord
--    notification template (scraper_health.discord.message, defined in
--    apps/web/monitoring/grafana/scraper-health-alerts.yaml) uses it to render
--    a concrete next step: "dispatch scraper-verify for club_id=NNN".
--
-- 2. One-extra-run series retention — the 20260703 views emit rows ONLY for
--    clubs currently in the firing condition, so a recovered club's series
--    vanishes on the next refresh and Grafana resolves the firing instance as
--    MissingSeries — churn-only "Resolved" spam in Discord (observed Jun 10-12
--    for Rodney's, Stevie Ray's, Comedy Clubhouse, Comedy Village). These
--    views instead keep a club's series for one extra run window: a club is
--    present iff its condition held in the LATEST run (flag 1) or in the
--    PREVIOUS run (flag 0). Every firing instance therefore sees an explicit
--    0 before its series disappears, resolving as Normal; a Normal instance's
--    later disappearance produces no notification.
--
--    Deliberately NOT one-row-per-club: Grafana's alert evaluator hard-caps a
--    query at 1000 series, and the latest run already spans ~1,559 clubs
--    (post-ticketmaster_national) — an unconditional per-club emit fails every
--    evaluation with "query evaluation returned too many results". The
--    firing-or-just-fired subset stays orders of magnitude below the cap.
--
-- The firing conditions themselves are unchanged from the 20260703 views:
--   - dropped_to_zero = 1 exactly when prev > 0 AND latest = 0 (fire-once
--     transition; the prev row must exist).
--   - consecutive_zero = 1 exactly when the last 2 consecutive FULL runs
--     (clubs_processed > 1) are both zero AND the club had shows within the
--     trailing 30 days (run_type IN ('scraper','verify') lookback). The prev
--     row must exist — a club absent from the previous full run is unknown,
--     not zero.
--
-- CREATE MATERIALIZED VIEW IF NOT EXISTS in the 20260703 migration means
-- editing that file in place would be a no-op on databases where the views
-- already exist — a definition change requires this DROP + recreate (see the
-- header comment in scraper-health-alerts.yaml). DROP discards existing
-- grants, so the grafana_ro GRANTs are re-applied below.

BEGIN;

DROP MATERIALIZED VIEW IF EXISTS mv_scraper_health_dropped_to_zero;
DROP MATERIALIZED VIEW IF EXISTS mv_scraper_health_consecutive_zero;

-- ---------------------------------------------------------------------------
-- Rule 2: prev>0 -> latest=0 transition, evaluated at the latest run (rn 1 vs
-- 2, flag value) and at the previous run (rn 2 vs 3, series retention only).
-- club_shows SUMs per (run_id, club_name) because scraper_run_clubs has no
-- UNIQUE on (run_id, club_name); MAX(club_id) collapses the same duplicates.
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW mv_scraper_health_dropped_to_zero AS
WITH runs AS (
    SELECT id,
           ROW_NUMBER() OVER (ORDER BY exported_at DESC) AS rn
    FROM scraper_runs
    WHERE run_type = 'scraper'
),
club_shows AS (
    SELECT c.run_id,
           c.club_name,
           MAX(c.club_id) AS club_id,
           SUM(c.num_shows) AS num_shows
    FROM scraper_run_clubs c
    JOIN runs ON runs.id = c.run_id AND runs.rn <= 3
    GROUP BY c.run_id, c.club_name
),
shows_at AS (
    SELECT r.rn, s.club_name, s.club_id, s.num_shows
    FROM club_shows s
    JOIN runs r ON r.id = s.run_id
),
transitions AS (
    SELECT cur.club_name, cur.club_id, cur.rn,
           CASE WHEN cur.num_shows = 0 AND prev.num_shows > 0 THEN 1 ELSE 0 END AS firing
    FROM shows_at cur
    JOIN shows_at prev
      ON prev.club_name = cur.club_name AND prev.rn = cur.rn + 1
    WHERE cur.rn <= 2
)
SELECT club_name AS club,
       COALESCE(MAX(club_id)::text, '') AS club_id,
       MAX(CASE WHEN rn = 1 THEN firing ELSE 0 END) AS dropped_to_zero
FROM transitions
GROUP BY club_name
HAVING MAX(firing) = 1
WITH DATA;

-- ---------------------------------------------------------------------------
-- Rule 2b: self-healing consecutive-zero companion, same one-extra-run series
-- retention. prev.num_shows = 0 (an actual zero row must exist in the
-- previous full run) keeps the 20260703 semantics; the 30-day history NOW()
-- anchor is baked at REFRESH time, tracking the daily cadence.
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW mv_scraper_health_consecutive_zero AS
WITH full_runs AS (
    SELECT id,
           ROW_NUMBER() OVER (ORDER BY exported_at DESC) AS rn
    FROM scraper_runs
    WHERE run_type = 'scraper'
      AND clubs_processed > 1
),
club_shows AS (
    SELECT c.run_id,
           c.club_name,
           MAX(c.club_id) AS club_id,
           SUM(c.num_shows) AS num_shows
    FROM scraper_run_clubs c
    JOIN full_runs fr ON fr.id = c.run_id AND fr.rn <= 3
    GROUP BY c.run_id, c.club_name
),
shows_at AS (
    SELECT r.rn, s.club_name, s.club_id, s.num_shows
    FROM club_shows s
    JOIN full_runs r ON r.id = s.run_id
),
history AS (
    SELECT c.club_name, MAX(c.num_shows) AS max_shows_30d
    FROM scraper_run_clubs c
    JOIN scraper_runs r ON r.id = c.run_id
    WHERE r.run_type IN ('scraper', 'verify')
      AND r.exported_at >= NOW() - INTERVAL '30 days'
    GROUP BY c.club_name
),
cond AS (
    SELECT cur.club_name, cur.club_id, cur.rn,
           CASE WHEN cur.num_shows = 0
                 AND prev.num_shows = 0
                 AND COALESCE(h.max_shows_30d, 0) > 0
                THEN 1
                ELSE 0
           END AS firing
    FROM shows_at cur
    JOIN shows_at prev
      ON prev.club_name = cur.club_name AND prev.rn = cur.rn + 1
    LEFT JOIN history h ON h.club_name = cur.club_name
    WHERE cur.rn <= 2
)
SELECT club_name AS club,
       COALESCE(MAX(club_id)::text, '') AS club_id,
       MAX(CASE WHEN rn = 1 THEN firing ELSE 0 END) AS consecutive_zero
FROM cond
GROUP BY club_name
HAVING MAX(firing) = 1
WITH DATA;

-- DROP discarded the 20260703 grants; re-grant. Guarded so the migration still
-- applies on databases (local/dev) where grafana_ro is absent. Kept in sync
-- with apps/web/prisma/scripts/create_grafana_readonly_role.sql.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grafana_ro') THEN
        GRANT SELECT ON
            public.mv_scraper_health_dropped_to_zero,
            public.mv_scraper_health_consecutive_zero
            TO grafana_ro;
    END IF;
END $$;

COMMIT;
