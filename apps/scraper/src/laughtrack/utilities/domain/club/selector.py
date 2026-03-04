"""
Club Selection Utility

Interactive utility for selecting clubs and scraper types from the command line.
"""

from typing import List, Optional

from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger


class ClubSelector:
    """Interactive club and scraper type selector."""

    def __init__(self):
        """Initialize with club handler."""
        self.club_handler = ClubHandler()

    def get_club_selection(self) -> List[Club]:
        """
        Interactive club selection from command line.

        Returns:
            List of selected clubs
        """
        Logger.info("Starting interactive club selection...")

        # Get all available clubs
        clubs = self.club_handler.get_all_clubs()

        if not clubs:
            Logger.error("No clubs found in database")
            return []

        # Display clubs (print once to show all at once)
        lines = ["\nAvailable clubs:"]
        for i, club in enumerate(clubs, 1):
            lines.append(f"{i:2d}. {club.name} ({club.scraper})")
        print("\n".join(lines))

        # Get user selection
        while True:
            try:
                selection = input("\nSelect club number (or 'q' to quit): ").strip()

                if selection.lower() == "q":
                    Logger.info("Club selection cancelled by user")
                    return []

                club_index = int(selection) - 1

                if 0 <= club_index < len(clubs):
                    selected_club = clubs[club_index]
                    Logger.info(f"Selected club: {selected_club.name}")
                    return [selected_club]
                else:
                    Logger.warning(f"Invalid selection. Please enter a number between 1 and {len(clubs)}")

            except ValueError:
                Logger.warning("Invalid input. Please enter a number or 'q' to quit")
            except KeyboardInterrupt:
                Logger.info("Club selection cancelled by user")
                return []

    def get_scraper_type_selection(self) -> Optional[str]:
        """
        Interactive scraper type selection from command line.

        Returns:
            Selected scraper type or None if cancelled
        """
        Logger.info("Starting interactive scraper type selection...")

        # Get unique scraper types
        all_clubs = self.club_handler.get_all_clubs()
        # Precompute counts in-memory to avoid per-line DB calls and make printing instantaneous
        counts: dict[str, int] = {}
        for club in all_clubs:
            if club.scraper:
                counts[club.scraper] = counts.get(club.scraper, 0) + 1
        # Stable, readable ordering
        scraper_types = sorted(counts.keys())

        if not scraper_types:
            Logger.error("No scraper types found in database")
            return None

        # Display scraper types (print once to show all at the same time)
        lines = ["\nAvailable scraper types:"]
        for i, scraper_type in enumerate(scraper_types, 1):
            club_count = counts.get(scraper_type, 0)
            lines.append(f"{i:2d}. {scraper_type} ({club_count} clubs)")
        print("\n".join(lines))

        # Get user selection
        while True:
            try:
                selection = input("\nSelect scraper type number (or 'q' to quit): ").strip()

                if selection.lower() == "q":
                    Logger.info("Scraper type selection cancelled by user")
                    return None

                scraper_index = int(selection) - 1

                if 0 <= scraper_index < len(scraper_types):
                    selected_scraper = scraper_types[scraper_index]
                    Logger.info(f"Selected scraper type: {selected_scraper}")
                    return selected_scraper
                else:
                    Logger.warning(f"Invalid selection. Please enter a number between 1 and {len(scraper_types)}")

            except ValueError:
                Logger.warning("Invalid input. Please enter a number or 'q' to quit")
            except KeyboardInterrupt:
                Logger.info("Scraper type selection cancelled by user")
                return None

    def get_multiple_club_selection(self) -> List[Club]:
        """
        Select multiple clubs interactively.

        Returns:
            List of selected clubs
        """
        Logger.info("Starting interactive multiple club selection...")

        clubs = self.club_handler.get_all_clubs()

        if not clubs:
            Logger.error("No clubs found in database")
            return []

        # Display clubs (print once to show all at once)
        lines = ["\nAvailable clubs:"]
        for i, club in enumerate(clubs, 1):
            lines.append(f"{i:2d}. {club.name} ({club.scraper})")
        print("\n".join(lines))

        print("\nSelect clubs (comma-separated numbers, e.g., '1,3,5' or 'all' for all clubs):")

        # Get user selection
        while True:
            try:
                selection = input("Selection: ").strip()

                if selection.lower() == "q":
                    Logger.info("Multiple club selection cancelled by user")
                    return []

                if selection.lower() == "all":
                    Logger.info(f"Selected all {len(clubs)} clubs")
                    return clubs

                # Parse comma-separated numbers
                indices = [int(x.strip()) - 1 for x in selection.split(",")]

                # Validate indices
                if all(0 <= i < len(clubs) for i in indices):
                    selected_clubs = [clubs[i] for i in indices]
                    club_names = [club.name for club in selected_clubs]
                    Logger.info(f"Selected {len(selected_clubs)} clubs: {', '.join(club_names)}")
                    return selected_clubs
                else:
                    Logger.warning(f"Invalid selection. All numbers must be between 1 and {len(clubs)}")

            except ValueError:
                Logger.warning("Invalid input. Please enter comma-separated numbers or 'all'")
            except KeyboardInterrupt:
                Logger.info("Multiple club selection cancelled by user")
                return []
