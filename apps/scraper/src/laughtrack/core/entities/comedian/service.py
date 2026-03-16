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

    def refresh_youtube_followers(self, api_key: str, batch_size: int = 50) -> int:
        """Fetch current YouTube subscriber counts and persist them.

        Args:
            api_key: YouTube Data API v3 key.
            batch_size: Max channel IDs per API request.

        Returns:
            Number of comedian rows updated.
        """
        Logger.info("Starting YouTube follower refresh.")
        try:
            return self.comedian_handler.refresh_youtube_followers(api_key, batch_size)
        except Exception as e:
            Logger.error(f"Error refreshing YouTube followers: {str(e)}")
            raise

    def refresh_instagram_followers(self) -> int:
        """Fetch current Instagram follower counts and persist them.

        Returns:
            Number of comedian rows updated.
        """
        Logger.info("Starting Instagram follower refresh.")
        try:
            return self.comedian_handler.refresh_instagram_followers()
        except Exception as e:
            Logger.error(f"Error refreshing Instagram followers: {str(e)}")
            raise

    def refresh_tiktok_followers(self) -> int:
        """Fetch current TikTok follower counts and persist them.

        Returns:
            Number of comedian rows updated.
        """
        Logger.info("Starting TikTok follower refresh.")
        try:
            return self.comedian_handler.refresh_tiktok_followers()
        except Exception as e:
            Logger.error(f"Error refreshing TikTok followers: {str(e)}")
            raise

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
