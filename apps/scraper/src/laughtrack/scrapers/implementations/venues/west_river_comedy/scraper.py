"""West River Comedy Club scraper backed by TicketTailor.

The venue website is still hosted on Wix, but its Shows nav and Full Schedule
CTA point to TicketTailor. TicketTailor serves Cloudflare challenges to plain
HTTP clients, so this scraper uses the scraper Playwright browser for listing
and detail pages, then reuses the shared JSON-LD extractor and transformer.
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor
from laughtrack.scrapers.implementations.json_ld.transformer import JsonLdTransformer
from laughtrack.shared.types import ScrapingTarget

from .data import WestRiverComedyPageData
from .extractor import extract_event_urls, extract_pagination_urls


class WestRiverComedyScraper(BaseScraper):
    """Scrape West River Comedy Club shows from its TicketTailor listing."""

    key = "west_river_comedy"
    _DEFAULT_LISTING_URL = "https://www.tickettailor.com/events/westrivercomedyclub"
    _MAX_LISTING_PAGES = 10

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(JsonLdTransformer(club))

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        listing_urls = [self.club.scraping_url or self._DEFAULT_LISTING_URL]
        visited_listing_urls: set[str] = set()
        event_urls: list[str] = []
        seen_event_urls: set[str] = set()

        while listing_urls and len(visited_listing_urls) < self._MAX_LISTING_PAGES:
            listing_url = listing_urls.pop(0)
            if listing_url in visited_listing_urls:
                continue
            visited_listing_urls.add(listing_url)

            html = await self._fetch_html_with_js(listing_url)
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: empty TicketTailor listing response: {listing_url}",
                    self.logger_context,
                )
                continue

            for event_url in extract_event_urls(html, base_url=listing_url):
                if event_url in seen_event_urls:
                    continue
                seen_event_urls.add(event_url)
                event_urls.append(event_url)

            for page_url in extract_pagination_urls(html, base_url=listing_url):
                if page_url not in visited_listing_urls and page_url not in listing_urls:
                    listing_urls.append(page_url)

        if listing_urls:
            Logger.warn(
                f"{self._log_prefix}: stopped TicketTailor listing pagination after "
                f"{self._MAX_LISTING_PAGES} pages",
                self.logger_context,
            )

        if not event_urls:
            Logger.warn(
                f"{self._log_prefix}: no TicketTailor event links found",
                self.logger_context,
            )
            return []

        Logger.info(
            f"{self._log_prefix}: discovered {len(event_urls)} TicketTailor event pages "
            f"across {len(visited_listing_urls)} listing pages",
            self.logger_context,
        )
        return event_urls

    async def get_data(self, target: ScrapingTarget) -> Optional[WestRiverComedyPageData]:
        html = await self._fetch_html_with_js(str(target))
        if not html:
            Logger.warn(
                f"{self._log_prefix}: empty TicketTailor event response: {target}",
                self.logger_context,
            )
            return None

        events = EventExtractor.extract_events(html)
        if not events:
            Logger.warn(
                f"{self._log_prefix}: no JSON-LD events found on TicketTailor page {target}",
                self.logger_context,
            )
            return None

        return WestRiverComedyPageData(event_list=events)
