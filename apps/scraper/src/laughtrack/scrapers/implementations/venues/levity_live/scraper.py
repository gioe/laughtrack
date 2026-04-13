"""Levity Live two-pass scraper.

Pass 1: Fetch calendar page, extract sameAs comic detail URLs from @graph JSON-LD.
Pass 2: Fetch each comic detail page to get per-showtime JSON-LD events.

The calendar page lists one entry per event (missing individual showtimes).
Comic detail pages contain separate JSON-LD blocks per showtime with unique
TicketWeb purchase URLs.
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.json_ld.transformer import JsonLdTransformer
from laughtrack.shared.logging import Logger

from .data import LevityLivePageData
from .extractor import LevityLiveExtractor


class LevityLiveScraper(BaseScraper):
    """Two-pass scraper for Levity Live venues (Huntsville, West Nyack, Oxnard)."""

    key = "levity_live"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(JsonLdTransformer(club))

    async def scrape_async(self) -> List[Show]:
        """Two-pass scrape: calendar page → comic detail pages."""
        try:
            calendar_url = self.club.scraping_url
            Logger.info(
                f"{self._log_prefix}: Fetching calendar page: {calendar_url}",
                self.logger_context,
            )

            # Pass 1: fetch calendar page and extract detail URLs
            calendar_html = await self.fetch_html(calendar_url)
            if not calendar_html:
                Logger.warn(
                    f"{self._log_prefix}: Empty response from calendar page",
                    self.logger_context,
                )
                return []

            detail_urls = LevityLiveExtractor.extract_detail_urls(calendar_html)
            if not detail_urls:
                Logger.warn(
                    f"{self._log_prefix}: No comic detail URLs found on calendar page",
                    self.logger_context,
                )
                return []

            Logger.info(
                f"{self._log_prefix}: Found {len(detail_urls)} comic detail pages to fetch",
                self.logger_context,
            )

            # Pass 2: fetch each detail page for per-showtime events
            targets = sorted(detail_urls)
            raw_data_results = await self._fetch_all_raw_data(targets)
            all_shows = self._transform_all_raw_data(raw_data_results)

            Logger.info(
                f"{self._log_prefix}: Scraped {len(all_shows)} total shows from {len(detail_urls)} detail pages",
                self.logger_context,
            )
            return all_shows

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: Scraping failed: {e}",
                self.logger_context,
            )
            raise
        finally:
            await self._cleanup_resources()

    async def get_data(self, target: str) -> Optional[LevityLivePageData]:
        """Fetch a single comic detail page and extract per-showtime events."""
        try:
            await self.rate_limiter.await_if_needed(target)
            html = await self.fetch_html(target)
            if not html:
                return None

            events = LevityLiveExtractor.extract_events_from_detail_page(html, target)
            if not events:
                Logger.debug(
                    f"{self._log_prefix}: No events found on detail page: {target}",
                    self.logger_context,
                )
                return None

            return LevityLivePageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: Error extracting data from {target}: {e}",
                self.logger_context,
            )
            return None
