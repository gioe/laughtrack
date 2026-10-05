"""Comix Roadhouse scraper implementation."""

import asyncio
from collections import defaultdict
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import ComixRoadhousePageData
from .extractor import ComixRoadhouseExtractor
from .transformer import ComixRoadhouseTransformer
from .pricing import checkout_url, extract_checkout

_CHECKOUT_TIMEOUT = 10
_CHECKOUT_BUDGET = 30


class ComixRoadhouseScraper(BaseScraper):
    """Scraper for Comix Roadhouse at Mohegan Sun."""

    key = "comix_roadhouse"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(ComixRoadhouseTransformer(club))

    async def get_data(self, url: str) -> Optional[ComixRoadhousePageData]:
        try:
            listing_urls = []
            seen_listing_pages = set()
            next_url = URLUtils.normalize_url(url)

            while next_url and next_url not in seen_listing_pages:
                seen_listing_pages.add(next_url)
                html_content = await self.fetch_html(next_url)
                if not html_content:
                    break

                listing_urls.extend(ComixRoadhouseExtractor.extract_listing_urls(html_content))
                next_url = ComixRoadhouseExtractor.extract_next_page_url(html_content, next_url)

            detail_urls = list(dict.fromkeys(listing_urls))
            events = []
            for detail_url in detail_urls:
                detail_html = await self.fetch_html(detail_url)
                if not detail_html:
                    continue
                events.extend(
                    ComixRoadhouseExtractor.extract_events_from_detail(
                        detail_html,
                        detail_url,
                        self.club.timezone or "America/New_York",
                    )
                )

            await self._enrich_checkouts(events)
            Logger.info(f"{self._log_prefix}: extracted {len(events)} Comix Roadhouse event(s)", self.logger_context)
            return ComixRoadhousePageData(event_list=events)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: failed to scrape Comix Roadhouse: {e}", self.logger_context)
            return None

    async def _enrich_checkouts(self, events) -> None:
        groups = defaultdict(list)
        for event in events:
            url = checkout_url(event.ticket_url)
            if url:
                groups[url].append(event)
        semaphore = asyncio.Semaphore(4)

        async def enrich(url, group):
            async with semaphore:
                try:
                    html = await asyncio.wait_for(self.fetch_html(url, skip_js_fallback=True), _CHECKOUT_TIMEOUT)
                    for event in group:
                        event.tickets, event.checkout_policies = extract_checkout(
                            html, event, self.club.timezone or "America/New_York"
                        )
                except Exception as exc:
                    Logger.warn(f"{self._log_prefix}: optional Comix checkout failed for {url}: {exc}")

        try:
            await asyncio.wait_for(
                asyncio.gather(*(enrich(url, group) for url, group in groups.items())), _CHECKOUT_BUDGET
            )
        except asyncio.TimeoutError:
            Logger.warn(f"{self._log_prefix}: Comix checkout budget exhausted; retaining venue performances")
