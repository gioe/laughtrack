"""
Scraping Result Processor

This module processes and saves scraping results, coordinating between
metrics collection, show saving, and result reporting.
"""

from typing import List

from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.show.service import ShowService
from laughtrack.foundation.models.operation_result import DatabaseOperationResult
from laughtrack.core.models.results import ClubScrapingResult, ScrapingSessionResult
from laughtrack.core.services.metrics import MetricsService
from laughtrack.foundation.infrastructure.logger.logger import Logger


class ScrapingResultProcessor:
    """Processes and saves scraping results."""

    def __init__(self):
        """Initialize with required services."""
        self.show_service = ShowService()
        self.metrics_service = MetricsService()

    def process_results(self, 
                        club_scraping_results: List[ClubScrapingResult]) -> DatabaseOperationResult:
        """
        Process scraping results and save shows to database.

        Args:
            shows: List of shows to save

        Returns:
            ScrapingResult with processed data and metrics
        """
        Logger.info("Saving scraping results...")
        all_shows = []

        for result in club_scraping_results:
            if result.shows:
                all_shows.extend(result.shows)

        self.metrics_service.start_session()
        db_results = self.show_service.insert_shows(all_shows)
        self.metrics_service.end_session(club_scraping_results, db_results)

        return db_results