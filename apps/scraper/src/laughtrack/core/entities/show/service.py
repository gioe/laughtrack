"""Service for orchestrating show operations with validation and batch processing."""

from typing import List, Optional

from laughtrack.foundation.models.operation_result import DatabaseOperationResult
from .handler import ShowHandler
from .model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger


class ShowService:
    """Service for orchestrating show operations with validation and batch processing."""

    def __init__(self):
        """Initialize the show service."""
        self.show_handler = ShowHandler()

    def insert_shows(self, 
                     shows: List[Show]) -> DatabaseOperationResult:
        """Save shows to database in batches with automatic validation and error handling.

        Args:
            shows: List of shows to save

        Returns:
            DatabaseOperationResult with operation counts
        """
        # Delegate to the ShowHandler which automatically handles batching
        if len(shows) == 0:
            Logger.info("No shows to save from scraping results")
            return DatabaseOperationResult()
        else:
            # Save shows to database
            Logger.info(f"Saving {len(shows)} shows to database...")
            return self.show_handler.insert_shows(shows)
            
    def update_show_popularity(self, show_ids: Optional[List[int]] = None) -> None:
        """
        Update popularity for shows in the database.

        Args:
            show_ids: Optional list of specific show IDs to update. If None, updates all shows.
        """
        Logger.info("Starting show popularity update.")

        try:
            # Get and validate show IDs using show service
            validated_show_ids = self.validate_and_get_show_ids(show_ids)

            if not validated_show_ids:
                Logger.warn("No shows found in database.")
                return

            # Use the show handler's connection management
            with self.show_handler.create_connection() as conn:
                # Delegate to show handler
                self.show_handler.calculate_and_update_popularity(validated_show_ids)

            Logger.info("Show popularity update completed successfully.")

        except Exception as e:
            Logger.error(f"Error updating show popularity: {str(e)}")
            raise

    def validate_and_get_show_ids(self, show_ids: Optional[List[int]] = None) -> List[int]:
        """Validate provided show IDs exist in database or fetch all show IDs if none provided.

        Args:
            show_ids: Optional list of specific show IDs to validate

        Returns:
            List of validated show IDs that exist in the database
        """
        try:
            if show_ids:
                # Delegate validation to show handler
                return self.show_handler.validate_show_ids(show_ids)
            else:
                # Get all show IDs from show handler
                all_ids = self.show_handler.get_all_show_ids()
                return all_ids
        except Exception as e:
            Logger.error(f"Error validating show IDs: {e}")
            raise
