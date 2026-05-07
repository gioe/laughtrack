"""Dr. Grins Comedy Club scraper using the venue's public BOB pages."""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import DrGrinsPageData
from .extractor import DrGrinsExtractor
from .transformer import DrGrinsEventTransformer

_PUBLIC_LISTING_URL = "https://www.thebob.com/drgrins/"


class DrGrinsScraper(BaseScraper):
    """Scraper for Dr. Grins Comedy Club (Grand Rapids, MI)."""

    key = "dr_grins"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            DrGrinsEventTransformer(club)
        )

    async def collect_scraping_targets(self) -> List[str]:
        """Collect public comedian detail pages from the BOB listing page."""
        html = await self.fetch_html(_PUBLIC_LISTING_URL)
        if not html:
            return [_PUBLIC_LISTING_URL]

        urls = DrGrinsExtractor.extract_detail_urls(html)
        if not urls:
            Logger.info(
                f"{self._log_prefix}: no public detail pages found",
                self.logger_context,
            )
            return [_PUBLIC_LISTING_URL]

        Logger.info(
            f"{self._log_prefix}: discovered {len(urls)} public detail page(s)",
            self.logger_context,
        )
        return urls

    async def get_data(self, url: str) -> Optional[DrGrinsPageData]:
        """Fetch a public detail page and extract dated performances."""
        try:
            html = await self.fetch_html(url)
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: empty response for {url}",
                    self.logger_context,
                )
                return None

            events = DrGrinsExtractor.extract_events(html, detail_url=url)
            if not events:
                Logger.info(
                    f"{self._log_prefix}: no events found on {url}",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} events from {url}",
                self.logger_context,
            )
            return DrGrinsPageData(event_list=events)

        except Exception as exc:
            Logger.error(
                f"{self._log_prefix}: error fetching {url}: {exc}",
                self.logger_context,
            )
            return None
