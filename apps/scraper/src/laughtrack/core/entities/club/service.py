"""
Club service for managing club information.

This service provides functionality for listing available clubs and scraper types,
reading directly from the database.
"""

import json
import sys
from typing import Dict, List, Optional
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

    def list_clubs_json(self) -> None:
        """Print all clubs as JSON (name, city, state, website) to stdout."""
        clubs = self.club_handler.get_all_clubs_json()
        json.dump(clubs, sys.stdout, indent=2)
        sys.stdout.write("\n")

    def find_club_by_name(self, name: str) -> Optional[Club]:
        """
        Find a club by name using case-insensitive matching.

        Tries exact match first, then falls back to partial (substring) match.
        Prints an error and returns None if no match or multiple partial matches
        are found.

        Args:
            name: Club name (or partial name) to search for

        Returns:
            Club if exactly one match found, None otherwise
        """
        needle = name.strip().lower()
        if not needle:
            Logger.error("Club name cannot be empty. Run 'make list-clubs' to see available venues.")
            return None

        try:
            all_clubs = self.club_handler.get_all_clubs()
        except Exception as e:
            Logger.error(f"Could not fetch clubs from database: {e}")
            return None

        # Exact match (case-insensitive)
        exact = [c for c in all_clubs if c.name.lower() == needle]
        if len(exact) == 1:
            return exact[0]
        if len(exact) > 1:
            # Defensive: club names are unique in the DB today, but guard against
            # future duplicates (e.g. after a botched import) rather than silently
            # returning the wrong club.
            names = ", ".join(c.name for c in exact)
            Logger.error(f"Ambiguous club name '{name}': multiple exact matches found: {names}")
            return None

        # Partial/substring match
        partial = [c for c in all_clubs if needle in c.name.lower()]
        if len(partial) == 1:
            Logger.info(f"Partial match: '{name}' → '{partial[0].name}' (ID: {partial[0].id})")
            return partial[0]
        if len(partial) > 1:
            names = "\n  ".join(f"ID {c.id}: {c.name}" for c in partial)
            Logger.error(
                f"Ambiguous club name '{name}': {len(partial)} partial matches found:\n  {names}\n"
                f"Use a more specific name or 'make scrape-club-id ID=<N>'"
            )
            return None

        Logger.error(
            f"No club found matching '{name}'. "
            f"Run 'make list-clubs' to see available venues."
        )
        return None

    def get_clubs_for_scraper(self, scraper_type: str) -> List[Club]:
        """
        Get all clubs that use a specific scraper type.

        Args:
            scraper_type: The scraper type to filter by

        Returns:
            List[Club]: List of clubs using the specified scraper type
        """
        return self.club_handler.get_clubs_for_scraper(scraper_type)

    def update_club_popularity(self, club_ids: Optional[List[int]] = None) -> None:
        """
        Recompute and persist popularity for clubs.

        Args:
            club_ids: Optional list of specific club IDs to update.  When
                ``None``, every active, visible club is considered.
        """
        Logger.info("Starting club popularity update.")

        try:
            self.club_handler.update_club_popularity(club_ids)
        except Exception as e:
            Logger.error(f"Error updating club popularity: {str(e)}")
            raise
