-- TASK-3584: Retune the consecutive-zero scraper-health alert.
--
-- Live triage on 2026-07-06 found the prior view firing on 105 clubs. The
-- dominant groups were successful Ticketmaster/Eventbrite aggregate scrapes
-- returning zero upstream items after one-off comedy listings aged out. That is
-- operational noise, not a scraper regression.
--
-- Keep the self-healing alert for clubs that are at zero for 2+ full scraper
-- runs AND still have a concrete reason to page:
--   * the latest or previous run failed,
--   * the latest or previous run detected a bot block, or
--   * LaughTrack still has future shows for the club, meaning persisted
--     inventory disagrees with the scraper's latest zero output.
--
-- This preserves one-extra-run series retention from TASK-2834. A club appears
-- when the condition holds for the latest run (consecutive_zero = 1) or held for
-- the previous run (consecutive_zero = 0), so Grafana resolves as Normal rather
-- than MissingSeries.

BEGIN;

DROP MATERIALIZED VIEW IF EXISTS mv_scraper_health_consecutive_zero;

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
           SUM(c.num_shows) AS num_shows,
           BOOL_OR(NOT COALESCE(c.success, FALSE)) AS has_failure,
           BOOL_OR(COALESCE(c.bot_block_detected, FALSE)) AS has_bot_block
    FROM scraper_run_clubs c
    JOIN full_runs fr ON fr.id = c.run_id AND fr.rn <= 3
    GROUP BY c.run_id, c.club_name
),
shows_at AS (
    SELECT r.rn,
           s.club_name,
           s.club_id,
           s.num_shows,
           s.has_failure,
           s.has_bot_block
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
current_future AS (
    SELECT club_id, COUNT(*) AS future_shows
    FROM shows
    WHERE date >= NOW()
    GROUP BY club_id
),
cond AS (
    SELECT cur.club_name, cur.club_id, cur.rn,
           CASE WHEN cur.num_shows = 0
                 AND prev.num_shows = 0
                 AND COALESCE(h.max_shows_30d, 0) > 0
                 AND (
                      cur.has_failure
                   OR prev.has_failure
                   OR cur.has_bot_block
                   OR prev.has_bot_block
                   OR COALESCE(cf.future_shows, 0) > 0
                 )
                THEN 1
                ELSE 0
           END AS firing
    FROM shows_at cur
    JOIN shows_at prev
      ON prev.club_name = cur.club_name AND prev.rn = cur.rn + 1
    LEFT JOIN history h ON h.club_name = cur.club_name
    LEFT JOIN current_future cf ON cf.club_id = cur.club_id
    WHERE cur.rn <= 2
)
SELECT club_name AS club,
       COALESCE(MAX(club_id)::text, '') AS club_id,
       MAX(CASE WHEN rn = 1 THEN firing ELSE 0 END) AS consecutive_zero
FROM cond
GROUP BY club_name
HAVING MAX(firing) = 1
WITH DATA;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grafana_ro') THEN
        GRANT SELECT ON
            public.mv_scraper_health_consecutive_zero
            TO grafana_ro;
    END IF;
END $$;

COMMIT;
