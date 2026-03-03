"""
High-level comedian statistics API service.

This module provides the main API interface for comedian statistics operations,
handling business logic for updating comedian show counts and statistics.
"""

from typing import List, Optional

from .handler import ComedianHandler
from laughtrack.foundation.infrastructure.logger.logger import Logger


class ComedianService:
    """High-level API for comedian statistics operations."""

    def __init__(self):
        """Initialize the ComedianService with necessary services."""
        self.comedian_handler = ComedianHandler()

    def update_comedian_popularity(self, comedian_uuids: Optional[List[str]] = None) -> None:
        """
        Update popularity for comedians in the database.

        Args:
            cursor: Database cursor
            comedian_uuids: Optional list of specific comedian UUIDs to update. If None, updates all comedians.
        """
        Logger.info("Starting comedian popularity update.")

        try:
            self.comedian_handler.update_comedian_popularity(comedian_uuids)
        except Exception as e:
            Logger.error(f"Error updating comedian popularity: {str(e)}")
            raise
