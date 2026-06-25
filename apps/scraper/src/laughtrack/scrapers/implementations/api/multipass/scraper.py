"""
Generic Multipass venue-listing scraper.

Multipass (multipass.com) is a server-rendered event-ticketing platform. Each
venue gets its own subdomain (e.g. ``denvercomedy.multipass.com``) whose root
page lists every upcoming show as a ``div.eventCard2026`` card with the title,
date/time, price and ticket URL all present in the static HTML — no detail-page
fetch is required.

This scraper is generic: a new Multipass venue needs only a ``scraping_sources``
row with ``scraper_key='multipass'`` and ``source_url`` set to the venue's
Multipass subdomain root.

Pipeline:
  1. collect_scraping_targets() → [club.scraping_url]   (single page, default)
  2. get_data(url)              → fetch HTML, extract MultipassEvents
  3. transformation_pipeline    → MultipassEvent.to_show() → Show objects
"""

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import MultipassPageData
from .extractor import MultipassExtractor
from .transformer import MultipassEventTransformer


class MultipassScraper(BaseScraper):
    """Generic scraper for Multipass venue box-office pages."""

    key = "multipass"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            MultipassEventTransformer(club)
        )

    async def get_data(self, url: str) -> Optional[MultipassPageData]:
        """Fetch the Multipass venue page and extract all upcoming events."""
        try:
            html = await self.fetch_html(url)
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: empty response for {url}",
                    self.logger_context,
                )
                return None

            events = MultipassExtractor.extract_events(html, url)
            if not events:
                self._warn_empty_extraction(url, html=html)
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} events from {url}",
                self.logger_context,
            )
            return MultipassPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching {url}: {e}",
                self.logger_context,
            )
            return None
