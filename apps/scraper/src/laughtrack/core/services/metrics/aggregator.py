"""Pure aggregation logic for metrics (ClubScrapingResult -> ScrapingSessionResult)."""

from __future__ import annotations
from typing import List

from laughtrack.core.models.metrics import PerClubStat, ErrorDetail
from laughtrack.core.models.results import ClubScrapingResult, ScrapingSessionResult
from laughtrack.core.entities.show.model import Show


class MetricsAggregator:
    def aggregate(self, results: List[ClubScrapingResult]) -> ScrapingSessionResult:
        all_shows: List[Show] = []
        errors: List[ErrorDetail] = []
        per_club_stats: List[PerClubStat] = []

        for result in results:
            all_shows.extend(result.shows)
            if result.error is not None:
                errors.append(
                    ErrorDetail(
                        club=result.club_name,
                        error=result.error,
                        execution_time=result.execution_time,
                    )
                )

            per_club_stats.append(
                PerClubStat(
                    club=result.club_name,
                    num_shows=len(result.shows),
                    execution_time=result.execution_time,
                    success=result.success,
                    # Per-club scrapes are a single attempt, so the only success
                    # signal available at aggregation time is the binary outcome
                    # (DB saves happen in bulk run-level and can't be attributed
                    # per club). Emit 100/0 so the persisted column is a real
                    # number the dashboards can chart — a meaningful reliability
                    # rate emerges as Grafana averages it across runs.
                    success_rate=(100.0 if result.success else 0.0),
                    error=(result.error if result.error is not None else None),
                    club_id=result.club_id,
                    errors=result.error_log_count,
                    http_status=result.http_status,
                    bot_block_detected=result.bot_block_detected,
                    bot_block_signature=result.bot_block_signature,
                    bot_block_provider=result.bot_block_provider,
                    bot_block_type=result.bot_block_type,
                    bot_block_source=result.bot_block_source,
                    bot_block_stage=result.bot_block_stage,
                    playwright_fallback_used=result.playwright_fallback_used,
                    items_before_filter=result.items_before_filter,
                )
            )
        return ScrapingSessionResult(shows=all_shows, errors=errors, per_club_stats=per_club_stats)

__all__ = ["MetricsAggregator"]
