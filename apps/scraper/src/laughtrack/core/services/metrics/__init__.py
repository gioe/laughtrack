"""
Metrics service package.

Public import path preserved: ``from laughtrack.core.services.metrics import MetricsService``.

Components:
 - MetricsService (facade/orchestrator)
 - aggregator (pure transformations)
 - repository (snapshot loading)
 - reporter (email notifications)
 - recorder (session lifecycle & counters)
 - dashboard (legacy HTML generator retained for reference)
"""

from typing import List, Optional
from datetime import datetime as _dt

from laughtrack.foundation.utilities.path.utils import ProjectPaths
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.core.models.metrics import ScrapingMetricsSnapshot
from laughtrack.core.models.results import ClubScrapingResult, ScrapingSessionResult
from laughtrack.foundation.models.operation_result import DatabaseOperationResult
from laughtrack.core.dashboard import generate_html_dashboard  # type: ignore

# Internal components
from .repository import MetricsRepository
from .reporter import MetricsReporter
from .aggregator import MetricsAggregator


class MetricsService:
    """Facade for metrics orchestration, delegating to specialized components."""

    def __init__(self) -> None:
        self.metrics_dir = ProjectPaths.get_metrics_dir()
        self._repo = MetricsRepository()
        self._reporter = MetricsReporter()
        self._aggregator = MetricsAggregator()

    # Compatibility no-op (retained for callers that still invoke it)
    def start_session(self) -> None:  # pragma: no cover - intentional no-op
        pass

    def end_session(self, club_results: List[ClubScrapingResult], db_operations: DatabaseOperationResult) -> None:
        session: ScrapingSessionResult = self._aggregator.aggregate(club_results or [])
        self._generate_and_save_dashboard(session, db_operations)
        self._process_latest_session_and_email()

    # ----------------- Internal orchestration helpers -----------------
    def _process_latest_session_and_email(self) -> bool:
        try:
            latest_snapshot = self._get_latest_snapshot()
            return self._reporter.send_session_email(latest_snapshot)
        except Exception as e:  # pragma: no cover - defensive
            Logger.error(f"Error processing session metrics for email: {e}")
            return False

    def _generate_and_save_dashboard(self, session: ScrapingSessionResult, db_operations: DatabaseOperationResult) -> None:
        try:
            snapshot = ScrapingMetricsSnapshot.from_session(session, db_operations, dt=_dt.now())
            self._render_and_save_dashboard(snapshot)
            self._persist_snapshot_json(snapshot)
        except Exception as e:  # pragma: no cover - defensive
            Logger.error(f"Failed to generate dashboard: {e}")

    def _render_and_save_dashboard(self, snapshot: ScrapingMetricsSnapshot) -> None:
        metrics_payload = [snapshot.to_full_json()]
        dashboard_path = ProjectPaths.get_dashboard_path()
        try:
            generate_html_dashboard(metrics_payload, str(dashboard_path))
            Logger.info(f"Dashboard generated successfully at {dashboard_path}")
        except Exception as e:  # pragma: no cover - defensive
            Logger.error(f"Failed to generate dashboard HTML: {e}")

    def _persist_snapshot_json(self, snapshot: ScrapingMetricsSnapshot) -> None:
        try:
            metrics_dir = ProjectPaths.get_metrics_dir()
            metrics_dir.mkdir(parents=True, exist_ok=True)
            ts = _dt.now().strftime('%Y%m%d_%H%M%S')
            json_path = metrics_dir / f"metrics_{ts}.json"
            import json as _json
            with open(json_path, "w", encoding="utf-8") as jf:
                _json.dump(snapshot.to_full_json(), jf, indent=2)
            Logger.info(f"Metrics snapshot JSON written to {json_path}")
        except Exception as write_err:  # pragma: no cover - defensive
            Logger.warn(f"Failed to write snapshot JSON: {write_err}")

    def _get_latest_snapshot(self) -> Optional[ScrapingMetricsSnapshot]:
        snaps = self._load_metrics_snapshots(count=1)
        return snaps[0] if snaps else None

    def _load_metrics_snapshots(self, count: Optional[int] = None) -> List[ScrapingMetricsSnapshot]:
        return self._repo.get_recent_snapshots(count=count if count is not None else 10)

    # ----------------- Public utilities -----------------
    def open_dashboard(self, open_in_browser: bool = True) -> bool:
        try:
            metrics = ProjectPaths.load_metrics_files()
            output_path = ProjectPaths.get_dashboard_path()
            generate_html_dashboard(metrics, str(output_path))
            if open_in_browser:
                import webbrowser as _wb  # local import
                _wb.open_new_tab(f"file://{output_path}")
            Logger.info(f"Opened dashboard: file://{output_path}")
            return True
        except Exception as e:  # pragma: no cover - defensive
            Logger.error(f"Failed to generate/open dashboard: {e}")
            return False

__all__ = ["MetricsService"]
