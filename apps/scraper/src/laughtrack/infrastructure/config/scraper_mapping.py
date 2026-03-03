"""Service for managing the mapping between scrapers and clubs.

This module discovers scraper implementations dynamically and maps club.scraper
keys to their corresponding scraper classes. It avoids circular imports by:
- Using TYPE_CHECKING for type-only hints
- Importing BaseScraper and ClubHandler at runtime within methods
- Dynamically importing scraper modules under laughtrack.scrapers.implementations
"""

from typing import TYPE_CHECKING, Dict, List, Optional, Type, cast, Any

from laughtrack.foundation.infrastructure.logger.logger import Logger

if TYPE_CHECKING:
    from laughtrack.core.entities.club import Club
    from laughtrack.scrapers.base.base_scraper import BaseScraper


class ScraperMapping:
    """Manage mapping between scraper keys and classes, and clubs to scrapers."""

    def __init__(self) -> None:
        # Import at runtime to avoid circular imports
        from laughtrack.core.entities.club import ClubHandler

        self.db_handler = ClubHandler()
        self._scraper_class_map: Optional[Dict[str, Type["BaseScraper"]]] = None
        self._club_mappings: Dict[Type["BaseScraper"], List["Club"]] = {}
        self._scrapers_loaded: bool = False

    def _import_scraper_modules(self) -> None:
        """Dynamically import all scraper modules so subclasses are registered."""
        if self._scrapers_loaded:
            return

        try:
            import importlib
            import pkgutil

            impl_root = importlib.import_module("laughtrack.scrapers.implementations")
            pkg_path: Optional[List[str]] = getattr(impl_root, "__path__", None)
            pkg_name: str = getattr(impl_root, "__name__", "laughtrack.scrapers.implementations")

            # Import only modules named *.scraper under implementations
            if pkg_path:
                for mod in pkgutil.walk_packages(pkg_path, pkg_name + "."):
                    name = mod.name
                    if name.endswith(".scraper"):
                        try:
                            importlib.import_module(name)
                        except Exception as e:  # Best-effort import; log and continue
                            Logger.warn(f"Failed importing scraper module {name}: {e}")

            self._scrapers_loaded = True
        except Exception as e:
            Logger.error(f"Error discovering scraper modules: {e}")
            # Still mark as loaded to avoid tight loops
            self._scrapers_loaded = True

    @property
    def scraper_class_map(self) -> Dict[str, Type["BaseScraper"]]:
        """Get mapping of scraper key -> scraper class, computed once and cached."""
        m = self._scraper_class_map
        if m is None:
            m = self._get_all_scrapers()
            self._scraper_class_map = m
        return m

    def _get_all_scrapers(self) -> Dict[str, Type["BaseScraper"]]:
        """Discover all scraper subclasses and return mapping by their keys."""
        # Ensure modules are imported so subclasses are registered
        self._import_scraper_modules()

        # Import at runtime to avoid cycles
        from laughtrack.scrapers.base.base_scraper import BaseScraper

        scrapers: Dict[str, Type["BaseScraper"]] = {}

        # Collect all subclasses recursively
        classes_to_check = [BaseScraper]
        while classes_to_check:
            current_class = classes_to_check.pop()
            for subclass in current_class.__subclasses__():
                k = getattr(subclass, "key", None)
                if isinstance(k, str) and k:
                    scrapers[k] = subclass
                classes_to_check.append(subclass)

        return scrapers

    def get_scraper_for_club(self, club: "Club") -> Optional[Type["BaseScraper"]]:
        """
        Get the scraper class for a given club based on its scraper field.

        Returns the scraper class, or None if the club has no scraper or unknown key.
        """
        s = getattr(club, "scraper", None)
        if not isinstance(s, str) or not s:
            return None

        scraper_class = self.scraper_class_map.get(s)
        if not scraper_class:
            available = list(self.scraper_class_map.keys())
            Logger.warn(f"Unknown scraper type: '{s}'. Available: {available}")
        return scraper_class

    def get_clubs_for_scraper(self, scraper_type: Type["BaseScraper"]) -> List["Club"]:
        """Return all clubs associated with a given scraper class."""
        if not self._club_mappings:
            self._load_club_mappings()
        return self._club_mappings.get(scraper_type, cast(List["Club"], []))

    def _load_club_mappings(self) -> None:
        """Load the mapping between scraper classes and their clubs from DB."""
        try:
            clubs = self.db_handler.get_all_clubs()

            club_mappings: Dict[Type["BaseScraper"], List["Club"]] = {}
            for club in clubs:
                scraper_class = self.get_scraper_for_club(club)
                if scraper_class:
                    if scraper_class not in club_mappings:
                        club_mappings[scraper_class] = []
                    club_mappings[scraper_class].append(club)

            self._club_mappings = club_mappings
        except Exception as e:
            Logger.error(f"Error loading club mappings: {e}")
            self._club_mappings = {}

    def clear_cache(self) -> None:
        """Clear cached mappings to force reload on next access."""
        self._scraper_class_map = None
        self._club_mappings = {}
        self._scrapers_loaded = False
