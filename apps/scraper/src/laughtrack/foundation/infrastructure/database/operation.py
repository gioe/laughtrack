"""
Database Operation Logger

Utility for logging database operations and batch processing results.
Provides detailed logging and metrics for database operations.
"""

from typing import List, Optional

from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import JSONDict


class DatabaseOperationLogger:
    """Utility for logging database operations and batch processing results."""

    @staticmethod
    def log_show_save_results(show_results: List[JSONDict], batch_size: int) -> None:
        """
        Log detailed results for show save operations.

        Args:
            show_results: List of show result dictionaries
            batch_size: Size of the original batch
        """
        if not show_results:
            Logger.warn(f"No show results to log for batch of {batch_size} shows")
            return

        # Count operation types
        inserts = sum(1 for result in show_results if result.get("operation_type") == "inserted")
        updates = sum(1 for result in show_results if result.get("operation_type") == "updated")
        unknown = sum(1 for result in show_results if result.get("operation_type") not in ["inserted", "updated"])

        # Log summary
        Logger.info(f"Show batch results: {len(show_results)} total ({inserts} inserts, {updates} updates)")

        if unknown > 0:
            Logger.warn(f"⚠️ {unknown} shows have unknown operation type")

        # Log individual show details (debug level)
        for result in show_results:
            club_id = result.get("club_id", "unknown")
            date = result.get("date", "unknown")
            operation = result.get("operation_type", "unknown")
            show_id = result.get("id", "unknown")
            Logger.debug(f"Show {show_id}: club_id={club_id}, date={date}, operation={operation}")

    @staticmethod
    def log_simple_batch_operation(operation: str, items_count: int, entity_type: str) -> None:
        """
        Log a simple batch operation result.

        Args:
            operation: Type of operation (INSERT, UPDATE, DELETE)
            items_count: Number of items affected
            entity_type: Type of entity being operated on
        """
        if items_count > 0:
            Logger.info(f"{operation} operation: {items_count} {entity_type} processed")
        else:
            Logger.warn(f"{operation} operation: No {entity_type} were processed")