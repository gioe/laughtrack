"""Scraping service package (public path preserved)."""

from typing import Optional, List

from laughtrack.app.scraper_resolver import ScraperResolver
from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.utilities.domain.club.selector import ClubSelector
from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.app.wiring import build_services  # noqa: F401 (side-effects for wiring if needed)
from laughtrack.core.models.results import ClubScrapingResult


class ScrapingService:
    def __init__(self):
        self.club_handler = ClubHandler()
        self.selector = ClubSelector()
        self._result_processor: Optional[ScrapingResultProcessor] = None
        self._scraping_resolver = ScraperResolver()

    @property
    def result_processor(self) -> ScrapingResultProcessor:
        if self._result_processor is None:
            self._result_processor = ScrapingResultProcessor()
        return self._result_processor

    def scrape_all_clubs(self) -> List[ClubScrapingResult]:
        Logger.info("Starting scrape of all clubs...")
        clubs = self.club_handler.get_all_clubs()
        if not clubs:
            raise ValueError("No clubs found with valid scraper configurations")
        Logger.info(f"Found {len(clubs)} clubs with scraper configurations")
        self._try_validate_scraper_keys(clubs)
        results = self._scrape_clubs(clubs)
        self.result_processor.process_results(results)
        return results

    def scrape_single_club(self, club_id: Optional[int] = None) -> None:
        Logger.info(f"Starting scrape of club: (ID: {club_id})")
        clubs = self.club_handler.get_clubs_by_ids([club_id]) if club_id else self.selector.get_club_selection()
        if not clubs:
            raise ValueError(f"Club with ID {club_id} not found" if club_id else "No club selected")
        results = self._scrape_clubs(clubs)
        self.result_processor.process_results(results)

    def scrape_by_scraper_type(self, scraper_type: Optional[str] = None) -> None:
        Logger.info(f"Starting scrape of all clubs using scraper type: {scraper_type}")
        scraper_type = scraper_type or self.selector.get_scraper_type_selection()
        if not scraper_type:
            raise ValueError(f"Unknown scraper type: {scraper_type}")
        clubs = self.club_handler.get_clubs_for_scraper(scraper_type)
        results = self._scrape_clubs(clubs)
        self.result_processor.process_results(results)

    # --- Internal helpers ---
    def _try_validate_scraper_keys(self, clubs: List[Club]) -> None:
        try:
            from laughtrack.app.validators.scraper_config import validate_scraper_keys_for_clubs
            validate_scraper_keys_for_clubs(clubs)
        except Exception as e:  # pragma: no cover - defensive
            Logger.warn(f"Scraper config validation skipped due to error: {e}")

    def _scrape_clubs(self, clubs: List[Club]) -> List[ClubScrapingResult]:
        results: List[ClubScrapingResult] = []
        for club in clubs:
            with Logger.use_context(club.as_context()):
                if not getattr(club, "scraper", None):
                    Logger.warn(f"Club '{club.name}' has no scraper key configured; skipping")
                    continue
                key: str = club.scraper if club.scraper is not None else ""
                scraper_cls = self._scraping_resolver.get(key)
                if not scraper_cls:
                    Logger.warn(f"No scraper found for club '{club.name}' with key '{key}'")
                    continue
                try:
                    scraper: BaseScraper = scraper_cls(club)
                    results.append(scraper.scrape_with_result())
                except Exception as e:  # pragma: no cover - defensive
                    Logger.error(f"Failed to scrape club '{club.name}': {e}")
                    results.append(
                        ClubScrapingResult(
                            club_name=club.name,
                            shows=[],
                            execution_time=0.0,
                            error=str(e),
                            club_id=club.id,
                        )
                    )
        return results

__all__ = ["ScrapingService"]
