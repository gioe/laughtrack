"""Fox Tucson Theatre custom scraper."""

from __future__ import annotations

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import FoxTucsonTheatrePageData
from .extractor import FoxTucsonTheatreExtractor
from .transformer import FoxTucsonTheatreTransformer


class FoxTucsonTheatreScraper(BaseScraper):
    """Scrape official comedy events from the Fox Tucson WordPress/Spektrix calendar."""

    key = "fox_tucson_theatre"
    DEFAULT_EVENTS_URL = "https://foxtucson.com/events/"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(FoxTucsonTheatreTransformer(club))

    async def collect_scraping_targets(self) -> List[str]:
        source_url = self.club.scraping_url or self.DEFAULT_EVENTS_URL
        return [URLUtils.normalize_url(source_url)]

    async def get_data(self, url: str) -> Optional[FoxTucsonTheatrePageData]:
        try:
            html_content = await self.fetch_html(url)
            event_list = FoxTucsonTheatreExtractor.extract_events(html_content or "", url)

            if not event_list:
                js_html = await self._fetch_html_with_js(url)
                event_list = FoxTucsonTheatreExtractor.extract_events(js_html or "", url)

            await self._enrich_spektrix_details(event_list)
            return FoxTucsonTheatrePageData(event_list=event_list)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: Error extracting data from {url}: {e}", self.logger_context)
            return None

    async def _enrich_spektrix_details(self, event_list) -> None:
        for event in event_list:
            if not event.ticket_url:
                continue

            try:
                ticket_html = await self.fetch_html(event.ticket_url)
                iframe_url = FoxTucsonTheatreExtractor.extract_spektrix_iframe_url(
                    ticket_html or "", event.ticket_url
                )
            except Exception as e:
                Logger.warn(
                    f"{self._log_prefix}: Failed to fetch Fox Tucson ticket page {event.ticket_url}: {e}"
                )
                continue

            if not iframe_url:
                continue

            event.spektrix_event_url = iframe_url
            event.spektrix_web_event_id = FoxTucsonTheatreExtractor.extract_web_event_id(iframe_url)

            try:
                spektrix_html = await self.fetch_html(iframe_url)
                event.spektrix_instance_ids = FoxTucsonTheatreExtractor.extract_spektrix_instance_ids(
                    spektrix_html or ""
                )
            except Exception as e:
                Logger.warn(
                    f"{self._log_prefix}: Failed to fetch Spektrix event page {iframe_url}: {e}"
                )
