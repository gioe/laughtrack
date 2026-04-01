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
                    error=(result.error if result.error is not None else None),
                    club_id=result.club_id,
                    errors=result.error_log_count,
                )
            )
        return ScrapingSessionResult(shows=all_shows, errors=errors, per_club_stats=per_club_stats)

__all__ = ["MetricsAggregator"]
