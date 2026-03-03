"""Session lifecycle & counters (wraps low-level ScrapingMetrics)."""

from __future__ import annotations
import time
from typing import List, Optional

from laughtrack.foundation.models.types import DuplicateKeyDetails
from laughtrack.foundation.utilities.path.utils import ProjectPaths
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.core.models.metrics import (
    ScrapingMetrics,
    DuplicateShowDetail,
    DuplicateShow,
    DBOperationsSummary,
)
from laughtrack.foundation.models.operation_result import DatabaseOperationResult


class MetricsRecorder:
    def __init__(self) -> None:
        self.metrics_dir = ProjectPaths.get_metrics_dir()
        self._current_session: Optional[ScrapingMetrics] = None
        self._session_start_time: Optional[float] = None

    # ---- Session lifecycle ----
    def start_session(self) -> None:
        self._current_session = ScrapingMetrics(str(self.metrics_dir))
        self._session_start_time = time.time()

    def end_session(self) -> bool:
        if not self._current_session:
            return False
        try:
            if self._session_start_time is not None:
                self._current_session.session_duration_seconds = max(
                    0.0, float(time.time() - self._session_start_time)
                )
            scraped = int(self._current_session.shows_scraped)
            saved = int(self._current_session.shows_saved)
            self._current_session.success_rate = (saved / scraped * 100.0) if scraped > 0 else 0.0
            self._current_session.export_metrics()
            Logger.info("Metrics session ended and saved successfully")
            return True
        except Exception as e:  # pragma: no cover
            Logger.error(f"Error ending metrics session: {e}")
            return False
        finally:
            self._current_session = None
            self._session_start_time = None

    # ---- Recording helpers ----
    def record_club_processed(self, execution_time: float, success: bool) -> None:
        if not self._current_session:
            return
        self._current_session.inc_clubs_processed()
        if success:
            self._current_session.inc_clubs_successful()
        else:
            self._current_session.inc_clubs_failed()
            self._current_session.inc_errors_total()
        self._current_session.add_execution_time(execution_time)

    def record_shows_scraped(self, count: int) -> None:
        if self._current_session:
            self._current_session.inc_shows_scraped(count)

    def record_show_db_operations(self, db_ops: DatabaseOperationResult) -> None:
        if not self._current_session or not db_ops:
            return
        skipped = sum(len(d.dropped) for d in (db_ops.duplicate_details or []))
        self._current_session.inc_shows_saved(db_ops.total)
        self._current_session.inc_shows_inserted(db_ops.inserts)
        self._current_session.inc_shows_updated(db_ops.updates)
        self._current_session.inc_shows_failed_save(db_ops.errors)
        if skipped:
            self._current_session.inc_shows_skipped_dedup(skipped)
        if db_ops.validation_errors:
            self._current_session.inc_shows_validation_failed(db_ops.validation_errors)
        if db_ops.db_errors:
            self._current_session.inc_shows_db_errors(db_ops.db_errors)
        self.attach_duplicate_details_metadata(db_ops.duplicate_details)

    def attach_duplicate_details_metadata(self, dupe_details: List[DuplicateKeyDetails]) -> None:
        session = self.get_current_session_metrics()
        if not session or len(dupe_details) == 0:
            return
        try:
            typed: List[DuplicateShowDetail] = []
            for d in dupe_details:
                kept = DuplicateShow(name=str(d.kept.name or ""), show_page_url=d.kept.show_page_url)
                dropped = [DuplicateShow(name=str(x.name or ""), show_page_url=x.show_page_url) for x in (d.dropped or [])]
                typed.append(
                    DuplicateShowDetail(
                        club_id=d.club_id,
                        club_name=None,
                        date=str(d.date or ""),
                        room=d.room,
                        kept=kept,
                        dropped=dropped,
                    )
                )
            session.append_duplicate_details(typed)
        except Exception:  # pragma: no cover - resilience
            pass

    # ---- Metadata setters ----
    def set_per_club_stats(self, stats) -> None:  # type: ignore[no-untyped-def]
        if self._current_session:
            try:
                self._current_session.set_per_club_stats(stats)
            except Exception:  # pragma: no cover
                Logger.warn("Failed to set per-club stats on metrics session")

    def set_error_details(self, errors) -> None:  # type: ignore[no-untyped-def]
        if self._current_session:
            try:
                self._current_session.set_error_details(errors)
            except Exception:  # pragma: no cover
                Logger.warn("Failed to set error details on metrics session")

    # ---- Accessors ----
    def get_current_session_metrics(self) -> Optional[ScrapingMetrics]:
        return self._current_session

    # ---- Utilities ----
    @staticmethod
    def build_db_operations_summary(db_ops: DatabaseOperationResult) -> DBOperationsSummary:
        skipped = sum(len(d.dropped) for d in (db_ops.duplicate_details or []))
        return DBOperationsSummary(
            total=db_ops.total,
            inserts=db_ops.inserts,
            updates=db_ops.updates,
            errors=db_ops.errors,
            duplicates_dropped=skipped,
            validation_errors=db_ops.validation_errors,
            db_errors=db_ops.db_errors,
        )

__all__ = ["MetricsRecorder"]
