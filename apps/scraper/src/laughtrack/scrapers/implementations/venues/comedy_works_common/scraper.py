"""Shared Comedy Works scraper flow."""

from dataclasses import dataclass
from typing import List, Optional, Type

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.venues.comedy_works_common.extractor import (
    ComedyWorksBaseExtractor,
)
from laughtrack.shared.types import ScrapingTarget
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

_BASE_URL = "https://www.comedyworks.com"


@dataclass(frozen=True)
class ComedyWorksLocationConfig:
    """Configuration that distinguishes one Comedy Works location scraper."""

    query_value: str
    location_label: str
    extractor_cls: Type[ComedyWorksBaseExtractor]
    page_data_cls: Type[EventListContainer]
    transformer_cls: Type[DataTransformer]


class ComedyWorksLocationScraper(BaseScraper):
    """Parameterized scraper for a Comedy Works location."""

    config: ComedyWorksLocationConfig

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            self.config.transformer_cls(club)
        )

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Fetch the configured events list page and return unique comedian slugs."""
        events_url = f"{_BASE_URL}/events?{self.config.query_value}"

        try:
            html = await self.fetch_html(events_url)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching events page: {e}",
                self.logger_context,
            )
            return []

        if not html:
            Logger.info(
                f"{self._log_prefix}: empty response from events page",
                self.logger_context,
            )
            return []

        slugs = self.config.extractor_cls.extract_comedian_slugs(html)

        Logger.info(
            f"{self._log_prefix}: found {len(slugs)} unique comedian slugs",
            self.logger_context,
        )
        return slugs

    async def get_data(self, target: ScrapingTarget) -> Optional[EventListContainer]:
        """Fetch a comedian detail page and extract configured-location showtimes."""
        slug = str(target)
        detail_url = f"{_BASE_URL}/comedians/{slug}"

        try:
            html = await self.fetch_html(detail_url)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching {detail_url}: {e}",
                self.logger_context,
            )
            return None

        if not html:
            Logger.info(
                f"{self._log_prefix}: empty response from {detail_url}",
                self.logger_context,
            )
            return None

        events = self.config.extractor_cls.extract_events_from_detail(html, slug)

        if not events:
            Logger.info(
                f"{self._log_prefix}: no {self.config.location_label} showtimes for {slug}",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: {events[0].name}: {len(events)} showtimes",
            self.logger_context,
        )
        return self.config.page_data_cls(event_list=events)
