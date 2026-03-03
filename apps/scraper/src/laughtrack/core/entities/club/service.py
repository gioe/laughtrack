"""
Club service for managing club information.

This service provides functionality for listing available clubs and scraper types,
reading directly from the database.
"""

from typing import List
from .handler import ClubHandler
from .model import Club

from laughtrack.foundation.infrastructure.logger.logger import Logger

class ClubService:
    """Service for managing club information and listings."""

    def __init__(self):
        """Initialize the ClubService with necessary dependencies."""
        self.club_handler = ClubHandler()

    def list_available_clubs(self) -> None:
        """List all available clubs with their IDs and names that have non-null scraper types."""
        all_clubs = self.club_handler.get_all_clubs()

        if not all_clubs:
            Logger.warn("No clubs found with scraper mappings")
            return

        # Build consolidated club listing
        club_info = []
        for club in all_clubs:
            scraper_type = club.scraper or "N/A"
            club_info.append(f"  ID: {club.id:2d} - {club.name:<35} ({scraper_type})")

        # Build usage examples
        usage_examples = [
            f"  make scrape-club-id ID={all_clubs[0].id}",
            f"  make scrape-club CLUB='{all_clubs[0].name}'",
        ]

        # Consolidated message with all information
        consolidated_message = (
            f"Available clubs with scraper mappings:\n"
            f"{chr(10).join(club_info)}\n\n"
            f"Total: {len(all_clubs)} clubs with scraper mappings\n\n"
            f"Usage examples:\n"
            f"{chr(10).join(usage_examples)}"
        )

        Logger.info(consolidated_message)

    def get_clubs_for_scraper(self, scraper_type: str) -> List[Club]:
        """
        Get all clubs that use a specific scraper type.

        Args:
            scraper_type: The scraper type to filter by

        Returns:
            List[Club]: List of clubs using the specified scraper type
        """
        return self.club_handler.get_clubs_for_scraper(scraper_type)
