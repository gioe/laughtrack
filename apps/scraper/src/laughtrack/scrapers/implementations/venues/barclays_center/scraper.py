"""Barclays Center scraper using the official comedy category page."""

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import BarclaysCenterPageData
from .extractor import BarclaysCenterExtractor
from .transformer import BarclaysCenterEventTransformer

_DEFAULT_CATEGORY_URL = "https://www.barclayscenter.com/events/category/comedy"


class BarclaysCenterScraper(BaseScraper):
    """Scraper for Barclays Center's official comedy category."""

    key = "barclays_center"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(BarclaysCenterEventTransformer(club))

    async def collect_scraping_targets(self):
        """Return the configured official comedy category URL."""
        return [self.club.scraping_url or _DEFAULT_CATEGORY_URL]

    async def get_data(self, url: str) -> Optional[BarclaysCenterPageData]:
        """Fetch the comedy category and enrich each event from its detail page."""
        try:
            html = await self.fetch_html(URLUtils.normalize_url(url))
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: empty response for {url}",
                    self.logger_context,
                )
                return None

            events = BarclaysCenterExtractor.extract_listing_events(html, url)
            if not events:
                Logger.info(
                    f"{self._log_prefix}: no comedy events found on {url}",
                    self.logger_context,
                )
                return None

            enriched = []
            for event in events:
                detail_html = await self.fetch_html(event.detail_url)
                enriched_event = BarclaysCenterExtractor.enrich_event_from_detail_page(
                    event,
                    detail_html or "",
                )
                if enriched_event.date_str and enriched_event.time_str:
                    enriched.append(enriched_event)
                else:
                    Logger.warn(
                        f"{self._log_prefix}: skipped event without detail date/time: {event.detail_url}",
                        self.logger_context,
                    )

            Logger.info(
                f"{self._log_prefix}: extracted {len(enriched)} comedy events from {url}",
                self.logger_context,
            )
            return BarclaysCenterPageData(event_list=enriched)

        except Exception as exc:
            Logger.error(
                f"{self._log_prefix}: error fetching {url}: {exc}",
                self.logger_context,
            )
            return None
