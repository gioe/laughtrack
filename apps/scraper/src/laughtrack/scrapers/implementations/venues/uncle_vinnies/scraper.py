"""
Uncle Vinnie's Comedy Club scraper.

This is a refactored multi-step scraper that follows the standardized 5-component architecture:
1. Scraper: Orchestration using BaseScraper pipeline
2. Extractor: Multi-step data extraction (calendar discovery → API calls)
3. Transformer: Data conversion to Show objects
4. PageData: Data models for extracted data
5. Event Model: Uncle Vinnie's specific event structure

The scraper follows Pattern C: Multi-Step API Workflow from the architecture patterns.
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.utilities.datetime import DateTimeUtils
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.utilities.infrastructure.scraper import log_filter_breakdown

from .data import UncleVinniesPageData
from .extractor import UncleVinniesExtractor
from .transformer import UncleVinniesEventTransformer


class UncleVinniesScraper(BaseScraper):
    """
    Multi-step scraper for Uncle Vinnie's Comedy Club following standardized architecture.

    Architecture:
    1. Discover event links from calendar pages (6 months)
    2. Extract production IDs from event URLs
    3. Fetch performance data from OvationTix API
    4. Transform to Show objects using standardized pipeline
    """

    key = "uncle_vinnies"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformer = UncleVinniesEventTransformer(club)

    async def discover_urls(self) -> List[str]:
        """
        For multi-step scrapers, return a single URL to trigger the workflow.
        The actual URL discovery happens in the extractor.

        Returns:
            Single URL to start the multi-step workflow
        """
        return [URLUtils.normalize_url(self.club.scraping_url)]

    async def get_data(self, url: str) -> Optional[UncleVinniesPageData]:
        """
        Extract Uncle Vinnie's event data using multi-step API workflow.

        The scraper performs all HTTP calls using BaseScraper utilities, while the
        extractor parses responses and builds models.

        Args:
            url: Base URL to start the multi-step workflow from

        Returns:
            UncleVinniesPageData containing extracted events or None if failed
        """
        try:
            base_url = URLUtils.normalize_url(url)

            # Prepare headers
            calendar_headers = BaseHeaders.get_headers(
                base_type="desktop_browser", domain=base_url, referer=base_url
            )
            api_headers = BaseHeaders.get_headers(
                base_type="json",
                domain="https://web.ovationtix.com",
                origin="https://ci.ovationtix.com",
                referer="https://ci.ovationtix.com/",
                clientId="35774",
                newCIRequest="true",
            )

            # Step 1: Discover event URLs across 6 months
            all_event_urls: List[str] = []
            for offset in range(6):
                date_str = DateTimeUtils.get_date_offset_from_now(offset)
                calendar_url = f"{base_url}/?date={date_str}"

                try:
                    html = await self.fetch_html(calendar_url, headers=calendar_headers)
                except Exception as e:
                    Logger.warn(f"Failed to fetch calendar {calendar_url}: {e}", self.logger_context)
                    continue

                month_urls = UncleVinniesExtractor.extract_event_urls_from_calendar_html(html, base_url=base_url)
                all_event_urls.extend(month_urls)
                Logger.info(f"Found {len(month_urls)} events on {calendar_url}", self.logger_context)

            # Deduplicate while preserving order
            seen = set()
            event_urls: List[str] = []
            for u in all_event_urls:
                if u not in seen:
                    seen.add(u)
                    event_urls.append(u)

            if not event_urls:
                Logger.warn("No event URLs discovered", self.logger_context)
                return None

            # Diagnostics: which URLs yield OvationTix production IDs prior to API calls
            log_filter_breakdown(
                event_urls,
                self.logger_context,
                id_getter=lambda u: UncleVinniesExtractor.extract_production_id(u),
                accept_predicate=lambda u: bool(UncleVinniesExtractor.extract_production_id(u)),
                label="OvationTix production discovery",
                name_getter=lambda u: u,
                date_getter=None,
            )

            # Step 2-4: For each event URL, extract production/performance and build events
            events = []
            for event_url in event_urls:
                try:
                    production_id = UncleVinniesExtractor.extract_production_id(event_url)
                    if not production_id:
                        Logger.debug(f"Skipping URL without production id: {event_url}", self.logger_context)
                        continue

                    # Query production summary to get next upcoming performance.
                    # OvationTix returns 404 for productions whose shows have all passed.
                    # We check the status code directly (bypassing fetch_json's retry logic)
                    # so we don't waste 4 retry attempts on a deterministic 404.
                    production_url = (
                        f"https://web.ovationtix.com/trs/api/rest/Production({production_id})/performance?"
                    )
                    session = await self.get_session()
                    production_raw = await session.get(production_url, headers=api_headers)
                    if production_raw.status_code == 404:
                        Logger.debug(
                            f"Production {production_id} has no upcoming performances (404 — past event)",
                            self.logger_context,
                        )
                        continue
                    production_raw.raise_for_status()
                    production_response = production_raw.json()

                    perf_id, start_date_str = UncleVinniesExtractor.extract_next_performance_info(production_response)
                    if not perf_id:
                        Logger.debug(
                            f"No upcoming performance for production {production_id}", self.logger_context
                        )
                        continue

                    if start_date_str and UncleVinniesExtractor.is_past_event(start_date_str, self.club.timezone):
                        Logger.debug(
                            f"Skipping past event for production {production_id}", self.logger_context
                        )
                        continue

                    performance_url = f"https://web.ovationtix.com/trs/api/rest/Performance({perf_id})"
                    performance_raw = await session.get(performance_url, headers=api_headers)
                    if performance_raw.status_code in (403, 404):
                        Logger.debug(
                            f"Performance {perf_id} not available (HTTP {performance_raw.status_code}) — skipping",
                            self.logger_context,
                        )
                        continue
                    performance_raw.raise_for_status()
                    performance_data = performance_raw.json()

                    event = UncleVinniesExtractor.create_event_from_performance_data(
                        performance_data, production_id, event_url
                    )
                    if event:
                        events.append(event)
                except Exception as e:
                    Logger.error(f"Failed processing {event_url}: {e}", self.logger_context)
                    continue

            if not events:
                Logger.warn("No events extracted from workflow", self.logger_context)
                return None

            Logger.info(f"Extracted {len(events)} events", self.logger_context)
            return UncleVinniesPageData(events)

        except Exception as e:
            Logger.error(f"Error extracting data: {e}", self.logger_context)
            return None
