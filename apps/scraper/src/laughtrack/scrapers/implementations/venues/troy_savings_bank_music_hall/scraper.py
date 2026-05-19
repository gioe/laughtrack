"""Troy Savings Bank Music Hall scraper using the official comedy listing."""

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import TroySavingsBankMusicHallPageData
from .extractor import TroySavingsBankMusicHallExtractor
from .transformer import TroySavingsBankMusicHallEventTransformer

_DEFAULT_EVENTS_URL = "https://www.troymusichall.org/events/?searchType=7"


class TroySavingsBankMusicHallScraper(BaseScraper):
    """Scraper for Troy Savings Bank Music Hall's official comedy events page."""

    key = "troy_savings_bank_music_hall"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            TroySavingsBankMusicHallEventTransformer(club)
        )

    async def collect_scraping_targets(self) -> list[str]:
        """Return the configured comedy listing URL."""
        return [self.club.scraping_url or _DEFAULT_EVENTS_URL]

    async def get_data(self, url: str) -> Optional[TroySavingsBankMusicHallPageData]:
        """Fetch Troy's comedy list page and enrich each event from its detail page."""
        normalized_url = URLUtils.normalize_url(url)
        try:
            html = await self.fetch_html(normalized_url)
            events = TroySavingsBankMusicHallExtractor.extract_listing_events(
                html or "",
                normalized_url,
            )
            if not events:
                Logger.info(
                    f"{self._log_prefix}: no Troy events found on {normalized_url}",
                    self.logger_context,
                )
                return None

            enriched = []
            for event in events:
                detail_html = await self.fetch_html(
                    TroySavingsBankMusicHallExtractor.detail_fetch_url(event.detail_url)
                )
                enriched.append(
                    TroySavingsBankMusicHallExtractor.enrich_event_from_detail_page(
                        event,
                        detail_html or "",
                    )
                )

            Logger.info(
                f"{self._log_prefix}: extracted {len(enriched)} Troy events from {normalized_url}",
                self.logger_context,
            )
            return TroySavingsBankMusicHallPageData(event_list=enriched)
        except Exception as exc:
            Logger.error(
                f"{self._log_prefix}: error fetching {normalized_url}: {exc}",
                self.logger_context,
            )
            return None
