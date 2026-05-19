"""Write scraper run summary snapshots to Postgres."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Iterable

from psycopg2.extras import Json, execute_values

from laughtrack.core.models.metrics import ErrorDetail, PerClubStat, ScrapingMetricsSnapshot
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.infrastructure.database.connection import get_transaction


class PipelineRunRecord:
    """Generic pipeline run summary for non-scraper operational jobs."""

    def __init__(
        self,
        *,
        pipeline_key: str,
        run_id: str,
        run_attempt: str,
        status: str,
        exported_at: datetime | None = None,
        duration_seconds: float = 0,
        raw_snapshot: dict[str, Any] | None = None,
    ) -> None:
        self.pipeline_key = pipeline_key
        self.run_id = run_id
        self.run_attempt = run_attempt
        self.status = status
        self.exported_at = exported_at or datetime.now(timezone.utc)
        self.duration_seconds = duration_seconds
        self.raw_snapshot = raw_snapshot or {}


class PostgresMetricsRepository:
    """Persist scraper run observability rows for admin-facing queries."""

    def persist_snapshot(self, snapshot: ScrapingMetricsSnapshot) -> bool:
        """Upsert a run and replace its child summaries idempotently."""
        run_key = self._run_key(snapshot)
        try:
            with get_transaction() as conn:
                with conn.cursor() as cur:
                    cur.execute(self._UPSERT_RUN_SQL, self._run_values(run_key, snapshot))
                    row = cur.fetchone()
                    run_id = row[0]

                    cur.execute("DELETE FROM scraper_run_clubs WHERE run_id = %s", (run_id,))
                    cur.execute("DELETE FROM scraper_run_errors WHERE run_id = %s", (run_id,))

                    club_rows = list(self._club_rows(run_id, snapshot.per_club_stats))
                    if club_rows:
                        execute_values(cur, self._INSERT_CLUBS_SQL, club_rows)

                    error_rows = list(self._error_rows(run_id, snapshot.error_details))
                    if error_rows:
                        execute_values(cur, self._INSERT_ERRORS_SQL, error_rows)

            Logger.info(f"Persisted scraper run summary to Postgres run_key={run_key}")
            return True
        except Exception as exc:  # pragma: no cover - production resilience
            Logger.warn(f"Failed to persist scraper run summary to Postgres: {exc}")
            return False

    def persist_pipeline_run(self, record: PipelineRunRecord) -> bool:
        """Upsert a generic pipeline run without scraper-specific child rows."""
        run_key = f"{record.pipeline_key}:{record.run_id}:{record.run_attempt}"
        success = record.status == "success"
        errors_total = 0 if success else 1
        success_rate = 100.0 if success else 0.0
        try:
            with get_transaction() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        self._UPSERT_RUN_SQL,
                        (
                            run_key,
                            record.exported_at.isoformat(),
                            record.duration_seconds,
                            0,
                            0,
                            0,
                            0,
                            0,
                            0,
                            0,
                            0,
                            0,
                            0,
                            0,
                            errors_total,
                            success_rate,
                            self._json_payload(record.raw_snapshot),
                        ),
                    )
                    row = cur.fetchone()
                    run_id = row[0]
                    cur.execute("DELETE FROM scraper_run_clubs WHERE run_id = %s", (run_id,))
                    cur.execute("DELETE FROM scraper_run_errors WHERE run_id = %s", (run_id,))

            Logger.info(f"Persisted pipeline run summary to Postgres run_key={run_key}")
            return True
        except Exception as exc:  # pragma: no cover - production resilience
            Logger.warn(f"Failed to persist pipeline run summary to Postgres: {exc}")
            return False

    @staticmethod
    def _run_key(snapshot: ScrapingMetricsSnapshot) -> str:
        exported_at = snapshot.session.exported_at or snapshot.timestamp or snapshot.datetime.isoformat()
        return f"scraper:{exported_at}"

    @staticmethod
    def _json_payload(value: Any) -> Json:
        return Json(value, dumps=lambda obj: json.dumps(obj, default=str))

    def _run_values(self, run_key: str, snapshot: ScrapingMetricsSnapshot) -> tuple[Any, ...]:
        return (
            run_key,
            snapshot.session.exported_at or snapshot.datetime.isoformat(),
            snapshot.session.duration_seconds,
            snapshot.shows.scraped,
            snapshot.shows.saved,
            snapshot.shows.inserted,
            snapshot.shows.updated,
            snapshot.shows.failed_save,
            snapshot.shows.skipped_dedup,
            snapshot.shows.validation_failed,
            snapshot.shows.db_errors,
            snapshot.clubs.processed,
            snapshot.clubs.successful,
            snapshot.clubs.failed,
            snapshot.errors.total,
            snapshot.success_rate,
            self._json_payload(snapshot.to_full_json()),
        )

    def _club_rows(self, run_id: int, stats: Iterable[PerClubStat]) -> Iterable[tuple[Any, ...]]:
        for ordinal, stat in enumerate(stats):
            yield (
                run_id,
                ordinal,
                stat.club,
                stat.club_id,
                stat.num_shows,
                stat.execution_time,
                stat.success,
                stat.error,
                stat.inserted,
                stat.updated,
                stat.saved,
                stat.failed_saves,
                stat.errors,
                stat.success_rate,
                stat.skipped_dedup,
                stat.validation_failed,
                stat.db_errors,
                stat.http_status,
                stat.bot_block_detected,
                stat.bot_block_signature,
                stat.bot_block_provider,
                stat.bot_block_type,
                stat.bot_block_source,
                stat.bot_block_stage,
                stat.playwright_fallback_used,
                stat.items_before_filter,
                self._json_payload(asdict(stat)),
            )

    def _error_rows(self, run_id: int, errors: Iterable[ErrorDetail]) -> Iterable[tuple[Any, ...]]:
        for ordinal, error in enumerate(errors):
            yield (
                run_id,
                ordinal,
                error.club,
                error.error,
                error.execution_time,
                self._json_payload(asdict(error)),
            )

    _UPSERT_RUN_SQL = """
        INSERT INTO scraper_runs (
            run_key,
            exported_at,
            duration_seconds,
            shows_scraped,
            shows_saved,
            shows_inserted,
            shows_updated,
            shows_failed_save,
            shows_skipped_dedup,
            shows_validation_failed,
            shows_db_errors,
            clubs_processed,
            clubs_successful,
            clubs_failed,
            errors_total,
            success_rate,
            raw_snapshot
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (run_key) DO UPDATE SET
            exported_at = EXCLUDED.exported_at,
            duration_seconds = EXCLUDED.duration_seconds,
            shows_scraped = EXCLUDED.shows_scraped,
            shows_saved = EXCLUDED.shows_saved,
            shows_inserted = EXCLUDED.shows_inserted,
            shows_updated = EXCLUDED.shows_updated,
            shows_failed_save = EXCLUDED.shows_failed_save,
            shows_skipped_dedup = EXCLUDED.shows_skipped_dedup,
            shows_validation_failed = EXCLUDED.shows_validation_failed,
            shows_db_errors = EXCLUDED.shows_db_errors,
            clubs_processed = EXCLUDED.clubs_processed,
            clubs_successful = EXCLUDED.clubs_successful,
            clubs_failed = EXCLUDED.clubs_failed,
            errors_total = EXCLUDED.errors_total,
            success_rate = EXCLUDED.success_rate,
            raw_snapshot = EXCLUDED.raw_snapshot,
            updated_at = NOW()
        RETURNING id
    """

    _INSERT_CLUBS_SQL = """
        INSERT INTO scraper_run_clubs (
            run_id,
            ordinal,
            club_name,
            club_id,
            num_shows,
            execution_time_seconds,
            success,
            error_message,
            shows_inserted,
            shows_updated,
            shows_saved,
            shows_failed_save,
            errors_count,
            success_rate,
            shows_skipped_dedup,
            shows_validation_failed,
            shows_db_errors,
            http_status,
            bot_block_detected,
            bot_block_signature,
            bot_block_provider,
            bot_block_type,
            bot_block_source,
            bot_block_stage,
            playwright_fallback_used,
            items_before_filter,
            raw_stat
        )
        VALUES %s
    """

    _INSERT_ERRORS_SQL = """
        INSERT INTO scraper_run_errors (
            run_id,
            ordinal,
            club_name,
            error_message,
            execution_time_seconds,
            raw_error
        )
        VALUES %s
    """


__all__ = ["PostgresMetricsRepository"]
