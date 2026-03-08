"""
Scraping Result Processor

This module processes and saves scraping results, coordinating between
metrics collection, show saving, and result reporting.
"""

from typing import List, Optional

from laughtrack.core.entities.show.service import ShowService
from laughtrack.foundation.models.operation_result import DatabaseOperationResult
from laughtrack.core.models.results import ClubScrapingResult
from laughtrack.core.services.metrics import MetricsService
from laughtrack.foundation.infrastructure.logger.logger import Logger


class ScrapingResultProcessor:
    """Processes and saves scraping results."""

    def __init__(self):
        """Initialize with required services."""
        self.show_service = ShowService()
        self.metrics_service = MetricsService()

    def start_run(self) -> None:
        """Mark the start of a scraping run before any per-club writes begin."""
        self.metrics_service.start_session()

    def insert_club_result(self, club_result: ClubScrapingResult) -> DatabaseOperationResult:
        """Persist shows for a single completed club immediately.

        Must be called while holding the caller's db_lock to ensure thread safety.
        """
        if not club_result.shows:
            return DatabaseOperationResult()
        Logger.info(f"Persisting {len(club_result.shows)} shows for '{club_result.club_name}'...")
        return self.show_service.insert_shows(club_result.shows)

    def process_results(
        self,
        club_scraping_results: List[ClubScrapingResult],
        db_result: Optional[DatabaseOperationResult] = None,
    ) -> DatabaseOperationResult:
        """Finalize scraping run: close metrics session.

        Shows are already persisted per-club by insert_club_result(); this method
        only runs the metrics/dashboard pipeline using the accumulated db_result.
        """
        Logger.info("Finalizing scraping results...")
        if db_result is None:
            db_result = DatabaseOperationResult()
        self.metrics_service.end_session(club_scraping_results, db_result)
        return db_result
