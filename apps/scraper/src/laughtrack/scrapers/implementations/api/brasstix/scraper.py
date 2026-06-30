"""Generic scraper for BrassTix inline calendar pages."""

from typing import Optional
from urllib.parse import parse_qs, urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.brasstix import BrassTixEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import BrassTixPageData
from .extractor import extract_brasstix_checkout_price, extract_brasstix_events
from .transformer import BrassTixTransformer


class BrassTixScraper(BaseScraper):
    """Scrape BrassTix calendar.php pages that embed eventArray JS data."""

    key = "brasstix"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self._checkout_price_by_show: dict[str, Optional[float]] = {}
        self.transformation_pipeline.register_transformer(BrassTixTransformer(club))

    async def get_data(self, url: str) -> Optional[BrassTixPageData]:
        normalized_url = URLUtils.normalize_url(url)
        try:
            html = await self.fetch_html(normalized_url)
            if not html:
                Logger.warn(f"{self._log_prefix}: BrassTix calendar returned empty HTML: {normalized_url}")
                return None

            events = extract_brasstix_events(html, normalized_url)
            if not events:
                Logger.warn(f"{self._log_prefix}: no BrassTix events found in {normalized_url}")
                return None
            await self._attach_checkout_prices(events)
            return BrassTixPageData(event_list=events)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: get_data failed for {normalized_url}: {e}", self.logger_context)
            return None

    async def _attach_checkout_prices(self, events: list[BrassTixEvent]) -> None:
        for event in events:
            cache_key = _checkout_price_cache_key(event)
            if cache_key not in self._checkout_price_by_show:
                self._checkout_price_by_show[cache_key] = await self._fetch_checkout_price(event.ticket_url)
            event.price = self._checkout_price_by_show[cache_key]

    async def _fetch_checkout_price(self, ticket_url: str) -> Optional[float]:
        try:
            html = await self.fetch_html(ticket_url)
        except Exception as e:
            Logger.warn(f"{self._log_prefix}: BrassTix checkout price fetch failed for {ticket_url}: {e}")
            return None

        price = extract_brasstix_checkout_price(html or "")
        if price is None:
            Logger.warn(f"{self._log_prefix}: BrassTix checkout price not found for {ticket_url}")
        return price


def _checkout_price_cache_key(event: BrassTixEvent) -> str:
    parsed = urlparse(event.ticket_url)
    show_param = parse_qs(parsed.query).get("Show", [""])[0].strip()
    return show_param or event.show_name or event.title
