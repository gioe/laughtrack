"""Soboba Casino Resort scraper using the venue's public calendar pages."""

from datetime import date
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import SobobaCasinoResortPageData
from .extractor import SobobaCasinoResortExtractor
from .transformer import SobobaCasinoResortEventTransformer

_DEFAULT_CALENDAR_URL = "https://soboba.com/entertainment/calendar"
_DEFAULT_MAX_MONTHS = 12


class SobobaCasinoResortScraper(BaseScraper):
    """Scraper for Soboba Casino Resort's entertainment calendar."""

    key = "soboba_casino_resort"

    def __init__(
        self,
        club: Club,
        *,
        max_months: int = _DEFAULT_MAX_MONTHS,
        start_date: Optional[date] = None,
        **kwargs,
    ):
        super().__init__(club, **kwargs)
        self.max_months = max(1, max_months)
        self.start_date = start_date
        self.transformation_pipeline.register_transformer(
            SobobaCasinoResortEventTransformer(club)
        )

    async def collect_scraping_targets(self) -> List[str]:
        """Return a bounded set of monthly calendar pages."""
        today = self.start_date or date.today()
        year = today.year
        month = today.month
        targets = []

        for offset in range(self.max_months):
            month_index = month + offset - 1
            target_year = year + (month_index // 12)
            target_month = (month_index % 12) + 1
            targets.append(
                f"https://soboba.com/entertainment/calendar/monthly/{target_year}/{target_month}/list"
            )

        return targets

    async def get_data(self, url: str) -> Optional[SobobaCasinoResortPageData]:
        """Fetch one Soboba calendar listing page and enrich its event cards."""
        try:
            html = await self.fetch_html(URLUtils.normalize_url(url))
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: empty response for {url}",
                    self.logger_context,
                )
                return None

            events = SobobaCasinoResortExtractor.extract_listing_events(html, url)
            if not events:
                Logger.info(
                    f"{self._log_prefix}: no events found on {url}",
                    self.logger_context,
                )
                return None

            enriched = []
            for event in events:
                detail_html = await self.fetch_html(event.detail_url)
                enriched_event = SobobaCasinoResortExtractor.enrich_event_from_detail_page(
                    event,
                    detail_html or "",
                )
                if SobobaCasinoResortExtractor.is_comedy_event(enriched_event):
                    enriched.append(enriched_event)

            Logger.info(
                f"{self._log_prefix}: extracted {len(enriched)} events from {url}",
                self.logger_context,
            )
            return SobobaCasinoResortPageData(event_list=enriched)

        except Exception as exc:
            Logger.error(
                f"{self._log_prefix}: error fetching {url}: {exc}",
                self.logger_context,
            )
            return None
