from datetime import datetime, timezone
from unittest.mock import patch

from laughtrack.core.models.metrics import (
    ClubsBlock,
    ErrorDetail,
    ErrorsBlock,
    PerClubStat,
    ScrapingMetricsSnapshot,
    SessionBlock,
    ShowsBlock,
)
from laughtrack.core.services.metrics import MetricsService
from laughtrack.core.services.metrics.postgres_repository import PipelineRunRecord, PostgresMetricsRepository
from laughtrack.core.models.results import ScrapingSessionResult
from laughtrack.foundation.models.operation_result import DatabaseOperationResult


class _Cursor:
    def __init__(self, valid_club_ids: list[int] | None = None) -> None:
        self.executed = []
        # Rows returned by the next fetchall(). The FK-filter SELECT in
        # persist_snapshot is the only path that calls fetchall(); tests that
        # don't construct with a list get an empty result (all club_ids treated
        # as unknown and nulled).
        self._fetchall_rows = [(cid,) for cid in (valid_club_ids or [])]

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return (42,)

    def fetchall(self):
        return list(self._fetchall_rows)


class _Connection:
    def __init__(self, cursor: _Cursor) -> None:
        self._cursor = cursor

    def cursor(self):
        return self._cursor


class _Transaction:
    def __init__(self, conn: _Connection) -> None:
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, *_args):
        return False


def _snapshot() -> ScrapingMetricsSnapshot:
    dt = datetime(2026, 5, 18, 12, 30, tzinfo=timezone.utc)
    return ScrapingMetricsSnapshot(
        timestamp=dt.isoformat(),
        datetime=dt,
        session=SessionBlock(duration_seconds=12.5, exported_at=dt.isoformat()),
        shows=ShowsBlock(scraped=3, saved=2, inserted=1, updated=1, failed_save=1),
        clubs=ClubsBlock(processed=2, successful=1, failed=1),
        errors=ErrorsBlock(total=1),
        success_rate=66.6,
        execution_times=[2.0, 10.5],
        per_club_stats=[
            PerClubStat(
                club="Good Club",
                club_id=7,
                num_shows=2,
                execution_time=2.0,
                success=True,
                http_status=200,
                items_before_filter=3,
            ),
            PerClubStat(
                club="Bad Club",
                club_id=8,
                num_shows=0,
                execution_time=10.5,
                success=False,
                error="timeout",
                bot_block_detected=True,
                bot_block_provider="cloudflare",
            ),
        ],
        error_details=[ErrorDetail(club="Bad Club", error="timeout", execution_time=10.5)],
    )


def test_scraper_run_summary_persistence_upserts_run_and_replaces_child_rows():
    cursor = _Cursor(valid_club_ids=[7, 8])
    captured_batches = []

    def fake_execute_values(cur, sql, rows):
        captured_batches.append((sql, list(rows)))

    with (
        patch(
            "laughtrack.core.services.metrics.postgres_repository.get_transaction",
            return_value=_Transaction(_Connection(cursor)),
        ),
        patch(
            "laughtrack.core.services.metrics.postgres_repository.execute_values",
            side_effect=fake_execute_values,
        ),
    ):
        result = PostgresMetricsRepository().persist_snapshot(_snapshot())

    assert result is True
    assert "INSERT INTO scraper_runs" in cursor.executed[0][0]
    assert cursor.executed[0][1][0] == "scraper:2026-05-18T12:30:00+00:00"
    assert cursor.executed[0][1][17] == "scraper"
    assert "ON CONFLICT (run_key) DO UPDATE" in cursor.executed[0][0]
    assert "DELETE FROM scraper_run_clubs" in cursor.executed[1][0]
    assert "DELETE FROM scraper_run_errors" in cursor.executed[2][0]
    assert "SELECT id FROM clubs WHERE id = ANY" in cursor.executed[3][0]

    club_sql, club_rows = captured_batches[0]
    error_sql, error_rows = captured_batches[1]
    assert "INSERT INTO scraper_run_clubs" in club_sql
    assert "INSERT INTO scraper_run_errors" in error_sql
    assert len(club_rows) == 2
    assert club_rows[0][2] == "Good Club"
    assert club_rows[0][3] == 7
    assert club_rows[1][3] == 8
    assert club_rows[1][7] == "timeout"
    assert len(error_rows) == 1
    assert error_rows[0][2] == "Bad Club"


def test_scraper_run_summary_persists_snapshot_run_type():
    """The persisted scraper_runs.run_type (param index 17) must come from
    snapshot.run_type, not a hardcoded literal. A single-club verify run carries
    run_type='verify' so the Grafana scraper-health alert rules — which whitelist
    run_type='scraper' — exclude it from the comparison windows/baselines (TASK-2831)."""
    snapshot = _snapshot()
    snapshot.run_type = "verify"
    cursor = _Cursor(valid_club_ids=[7, 8])

    with (
        patch(
            "laughtrack.core.services.metrics.postgres_repository.get_transaction",
            return_value=_Transaction(_Connection(cursor)),
        ),
        patch(
            "laughtrack.core.services.metrics.postgres_repository.execute_values",
        ),
    ):
        result = PostgresMetricsRepository().persist_snapshot(snapshot)

    assert result is True
    assert "INSERT INTO scraper_runs" in cursor.executed[0][0]
    assert cursor.executed[0][1][17] == "verify"


def test_scraper_run_summary_nullifies_unknown_club_ids_to_satisfy_fk():
    """Synthetic production_company proxies carry the SYNTHETIC_PROXY_PLACEHOLDER_ID
    sentinel (0) plus is_synthetic=True; deleted clubs leave stale positive ids in
    per_club_stats. Both must be nulled before INSERT or scraper_run_clubs_club_id_fkey
    raises and aborts the transaction (run 26762966336 incident, TASK-2552/2565)."""
    from laughtrack.core.entities.club.model import Club

    dt = datetime(2026, 5, 18, 12, 30, tzinfo=timezone.utc)
    snapshot = ScrapingMetricsSnapshot(
        timestamp=dt.isoformat(),
        datetime=dt,
        session=SessionBlock(duration_seconds=1.0, exported_at=dt.isoformat()),
        shows=ShowsBlock(),
        clubs=ClubsBlock(),
        errors=ErrorsBlock(),
        success_rate=0.0,
        execution_times=[],
        per_club_stats=[
            PerClubStat(club="Real Club", club_id=7, num_shows=0, execution_time=0.0, success=True),
            PerClubStat(
                club="Improbable Comedy (organizer)",
                club_id=Club.SYNTHETIC_PROXY_PLACEHOLDER_ID,
                num_shows=0,
                execution_time=0.0,
                success=True,
                is_synthetic=True,
                production_company_id=2,
            ),
            PerClubStat(club="Deleted Club", club_id=999, num_shows=0, execution_time=0.0, success=False),
            PerClubStat(club="Unknown ID Club", club_id=None, num_shows=0, execution_time=0.0, success=False),
        ],
        error_details=[],
    )
    # Only club 7 exists; the synthetic placeholder (0) and stale 999 must be nulled.
    cursor = _Cursor(valid_club_ids=[7])
    captured_batches = []

    def fake_execute_values(cur, sql, rows):
        captured_batches.append((sql, list(rows)))

    with (
        patch(
            "laughtrack.core.services.metrics.postgres_repository.get_transaction",
            return_value=_Transaction(_Connection(cursor)),
        ),
        patch(
            "laughtrack.core.services.metrics.postgres_repository.execute_values",
            side_effect=fake_execute_values,
        ),
    ):
        result = PostgresMetricsRepository().persist_snapshot(snapshot)

    assert result is True
    select_sql, select_params = cursor.executed[3]
    assert "SELECT id FROM clubs WHERE id = ANY" in select_sql
    assert sorted(select_params[0]) == [0, 7, 999]

    _, club_rows = captured_batches[0]
    by_name = {row[2]: row[3] for row in club_rows}
    assert by_name == {
        "Real Club": 7,
        "Improbable Comedy (organizer)": None,
        "Deleted Club": None,
        "Unknown ID Club": None,
    }


def test_scraper_run_summary_skips_validation_query_when_no_club_ids():
    """If per_club_stats has no non-null club_ids, skip the SELECT entirely —
    Postgres rejects ANY(ARRAY[]) and the round-trip is wasted work."""
    dt = datetime(2026, 5, 18, 12, 30, tzinfo=timezone.utc)
    snapshot = ScrapingMetricsSnapshot(
        timestamp=dt.isoformat(),
        datetime=dt,
        session=SessionBlock(duration_seconds=0.0, exported_at=dt.isoformat()),
        shows=ShowsBlock(),
        clubs=ClubsBlock(),
        errors=ErrorsBlock(),
        success_rate=0.0,
        execution_times=[],
        per_club_stats=[],
        error_details=[],
    )
    cursor = _Cursor()

    with (
        patch(
            "laughtrack.core.services.metrics.postgres_repository.get_transaction",
            return_value=_Transaction(_Connection(cursor)),
        ),
        patch(
            "laughtrack.core.services.metrics.postgres_repository.execute_values",
        ),
    ):
        PostgresMetricsRepository().persist_snapshot(snapshot)

    assert not any("SELECT id FROM clubs" in sql for sql, _ in cursor.executed)


def test_generic_pipeline_run_persistence_upserts_run_and_clears_child_rows():
    cursor = _Cursor()

    with patch(
        "laughtrack.core.services.metrics.postgres_repository.get_transaction",
        return_value=_Transaction(_Connection(cursor)),
    ):
        result = PostgresMetricsRepository().persist_pipeline_run(
            PipelineRunRecord(
                pipeline_key="github_actions_web_ci",
                run_id="123",
                run_attempt="2",
                status="failure",
                exported_at=datetime(2026, 5, 19, 12, 30, tzinfo=timezone.utc),
                raw_snapshot={"workflow_name": "Web CI"},
            )
        )

    assert result is True
    assert "INSERT INTO scraper_runs" in cursor.executed[0][0]
    assert cursor.executed[0][1][0] == "github_actions_web_ci:123:2"
    assert cursor.executed[0][1][14] == 1
    assert cursor.executed[0][1][15] == 0.0
    assert cursor.executed[0][1][17] == "pipeline"
    assert "DELETE FROM scraper_run_clubs" in cursor.executed[1][0]
    assert "DELETE FROM scraper_run_errors" in cursor.executed[2][0]


def test_scraper_run_refreshes_health_summary_views():
    """After a full 'scraper' run persists, the precomputed scraper-health
    materialized views must be REFRESHed so Grafana reads current data instead of
    rescanning scraper_runs/scraper_run_clubs on every evaluation (TASK-3573)."""
    cursor = _Cursor(valid_club_ids=[7, 8])

    with (
        patch(
            "laughtrack.core.services.metrics.postgres_repository.get_transaction",
            return_value=_Transaction(_Connection(cursor)),
        ),
        patch("laughtrack.core.services.metrics.postgres_repository.execute_values"),
    ):
        result = PostgresMetricsRepository().persist_snapshot(_snapshot())

    assert result is True
    refreshed = [sql for sql, _ in cursor.executed if "REFRESH MATERIALIZED VIEW" in sql]
    assert refreshed == [
        "REFRESH MATERIALIZED VIEW mv_scraper_health_overall",
        "REFRESH MATERIALIZED VIEW mv_scraper_health_dropped_to_zero",
        "REFRESH MATERIALIZED VIEW mv_scraper_health_consecutive_zero",
    ]


def test_verify_run_does_not_refresh_health_summary_views():
    """Single-club verify runs (and generic pipeline runs) are excluded from the
    scraper-health comparison windows by run_type, so refreshing the summary views
    after one would be wasted work — only run_type='scraper' triggers a refresh."""
    snapshot = _snapshot()
    snapshot.run_type = "verify"
    cursor = _Cursor(valid_club_ids=[7, 8])

    with (
        patch(
            "laughtrack.core.services.metrics.postgres_repository.get_transaction",
            return_value=_Transaction(_Connection(cursor)),
        ),
        patch("laughtrack.core.services.metrics.postgres_repository.execute_values"),
    ):
        result = PostgresMetricsRepository().persist_snapshot(snapshot)

    assert result is True
    assert not any("REFRESH MATERIALIZED VIEW" in sql for sql, _ in cursor.executed)


def test_health_summary_refresh_swallows_db_errors():
    """A refresh failure (e.g. the MVs not yet created on a fresh DB) is
    best-effort: refresh_health_summary logs and returns False rather than
    raising, so the exception can never propagate out of persist_snapshot and
    roll back the already-committed run."""

    class _RaisingCursor(_Cursor):
        def execute(self, sql, params=None):
            super().execute(sql, params)
            if "REFRESH MATERIALIZED VIEW" in sql:
                raise RuntimeError('relation "mv_scraper_health_overall" does not exist')

    cursor = _RaisingCursor()

    with patch(
        "laughtrack.core.services.metrics.postgres_repository.get_transaction",
        return_value=_Transaction(_Connection(cursor)),
    ):
        result = PostgresMetricsRepository().refresh_health_summary()

    assert result is False


def test_metrics_service_keeps_json_and_dashboard_path_when_postgres_persistence_runs():
    service = MetricsService()
    session = ScrapingSessionResult(shows=[], errors=[], per_club_stats=[])

    with (
        patch.object(service, "_render_and_save_dashboard") as render_dashboard,
        patch.object(service, "_persist_snapshot_json") as persist_json,
        patch.object(service._postgres_repo, "persist_snapshot", return_value=True) as persist_postgres,
    ):
        service._generate_and_save_dashboard(session, DatabaseOperationResult())

    render_dashboard.assert_called_once()
    persist_json.assert_called_once()
    persist_postgres.assert_called_once()
