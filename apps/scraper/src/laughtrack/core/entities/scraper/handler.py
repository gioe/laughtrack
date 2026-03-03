"""Scraper entity handler for scraper-related operations."""

from laughtrack.core.data.base_handler import BaseDatabaseHandler
from sql.club_queries import ClubQueries

from laughtrack.core.entities.scraper.model import Scraper
from laughtrack.foundation.infrastructure.logger.logger import Logger


class ScraperHandler(BaseDatabaseHandler[Scraper]):
    """Handler for scraper database operations."""

    def get_entity_name(self) -> str:
        """Return the entity name for logging purposes."""
        return "scraper"

    def get_entity_class(self) -> type[Scraper]:
        """Return the Scraper class for instantiation."""
        return Scraper

    def list_available_scraper_types(self) -> None:
        """List all available scraper types and their club counts from the database."""
        try:
            # Get scraper types directly from database
            results = self.execute_with_cursor(ClubQueries.GET_DISTINCT_SCRAPER_TYPES, return_results=True)
            if not results:
                Logger.warn("No scraper types found in database")
                return

            # Convert results to Scraper objects
            scrapers = [Scraper.from_db_row(row) for row in results]
            Logger.info(f"Retrieved {len(scrapers)} scrapers from database")

            # Build consolidated message
            scraper_info = []
            for scraper_summary in scrapers:
                scraper_info.append(f"  {scraper_summary.scraper_type}: {scraper_summary.club_count} clubs")

            consolidated_message = "Available scraper types:\n" + "\n".join(scraper_info)
            Logger.info(consolidated_message)

        except Exception as e:
            Logger.error(f"Error fetching scrapers: {str(e)}")
            raise
