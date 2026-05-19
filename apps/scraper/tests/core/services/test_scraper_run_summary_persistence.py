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
    def __init__(self) -> None:
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return (42,)


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
    cursor = _Cursor()
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
    assert "ON CONFLICT (run_key) DO UPDATE" in cursor.executed[0][0]
    assert "DELETE FROM scraper_run_clubs" in cursor.executed[1][0]
    assert "DELETE FROM scraper_run_errors" in cursor.executed[2][0]

    club_sql, club_rows = captured_batches[0]
    error_sql, error_rows = captured_batches[1]
    assert "INSERT INTO scraper_run_clubs" in club_sql
    assert "INSERT INTO scraper_run_errors" in error_sql
    assert len(club_rows) == 2
    assert club_rows[0][2] == "Good Club"
    assert club_rows[1][7] == "timeout"
    assert len(error_rows) == 1
    assert error_rows[0][2] == "Bad Club"


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
    assert "DELETE FROM scraper_run_clubs" in cursor.executed[1][0]
    assert "DELETE FROM scraper_run_errors" in cursor.executed[2][0]


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
