"""Club database handler for club-specific operations."""

from typing import List, Optional

from sql.club_queries import ClubQueries

from laughtrack.core.data.base_handler import BaseDatabaseHandler
from laughtrack.foundation.infrastructure.logger.logger import Logger

from .model import Club


class ClubHandler(BaseDatabaseHandler[Club]):
    """Handler for club database operations."""

    def get_entity_name(self) -> str:
        """Return the entity name for logging purposes."""
        return "club"

    def get_entity_class(self) -> type[Club]:
        """Return the Club class for instantiation."""
        return Club

    def get_all_clubs(self) -> List[Club]:
        """
        Fetch all clubs with non-null scrapers from database.

        Returns:
            List[Club]: List of all active clubs
        """
        try:
            results = self.execute_with_cursor(ClubQueries.GET_ALL_CLUBS, return_results=True)
            if not results:
                raise ValueError("No clubs found in database")

            Logger.info(f"Retrieved {len(results)} clubs from database")
            return [Club.from_db_row(row) for row in results]

        except Exception as e:
            Logger.error(f"Error fetching clubs: {str(e)}")
            raise

    def get_clubs_by_ids(self, club_ids: List[int]) -> List[Club]:
        """
        Fetch clubs by their IDs.

        Args:
            club_ids: List of club IDs to retrieve, or a single ID in a list

        Returns:
            List[Club]: List of clubs matching the provided IDs
        """
        if not club_ids:
            Logger.info("No club IDs provided")
            return []

        try:
            results = self.execute_with_cursor(ClubQueries.GET_CLUB_BY_IDS, (club_ids,), return_results=True)
            if not results:
                raise ValueError(f"No clubs found for IDs: {club_ids}")

            Logger.info(f"Retrieved {len(results)} clubs for {len(club_ids)} requested IDs")
            return [Club.from_db_row(row) for row in results]

        except Exception as e:
            Logger.error(f"Error fetching clubs {club_ids}: {str(e)}")
            raise

    def get_club_by_id(self, club_id: int) -> Optional[Club]:
        """
        Fetch a single club by its ID.

        Args:
            club_id: The club ID to retrieve

        Returns:
            Club | None: The club if found, None otherwise
        """
        if not club_id:
            raise ValueError("No club ID provided")

        clubs = self.get_clubs_by_ids([club_id])
        return clubs[0] if clubs else None

    def get_specific_clubs(self, club_ids: List[int]) -> List[Club]:
        """
        Fetch specific clubs by their IDs.

        Deprecated: Use get_clubs_by_ids instead.

        Args:
            club_ids: List of club IDs to retrieve

        Returns:
            List[Club]: List of clubs matching the provided IDs
        """
        return self.get_clubs_by_ids(club_ids)

    def get_clubs_for_scraper(self, scraper_type: str) -> List[Club]:
        """
        Fetch all clubs that use a specific scraper type.

        Args:
            scraper_type: The scraper type to filter clubs by

        Returns:
            List[Club]: List of clubs using the specified scraper type
        """
        if not scraper_type:
            raise ValueError("No scraper type provided")

        try:
            results = self.execute_with_cursor(ClubQueries.GET_CLUBS_BY_SCRAPER, (scraper_type,), return_results=True)
            if not results:
                raise ValueError(f"No clubs found for scraper type: {scraper_type}")

            Logger.info(f"Retrieved {len(results)} clubs for scraper type '{scraper_type}'")
            return [Club.from_db_row(row) for row in results]

        except Exception as e:
            Logger.error(f"Error fetching clubs for scraper '{scraper_type}': {str(e)}")
            raise
