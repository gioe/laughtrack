"""
Club service for managing club information.

This service provides functionality for listing available clubs and scraper types,
reading directly from the database.
"""

from .handler import ScraperHandler


class ScraperService:
    """Service for managing club information and listings."""

    def __init__(self):
        """Initialize the ScraperService with necessary dependencies."""
        self.scraper_handler = ScraperHandler()

    def list_available_scraper_types(self) -> None:
        """List all available scraper types and their club counts from the database."""
        self.scraper_handler.list_available_scraper_types()
