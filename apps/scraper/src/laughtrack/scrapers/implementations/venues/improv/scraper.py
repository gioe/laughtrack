"""
Improv multi-step scraper for improv.com venues.

This scraper discovers event links from the club's calendar page, then scrapes each event page for JSON-LD event data.
Follows the standardized 5-component architecture pattern.
"""

from typing import List, Optional
from urllib.parse import urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.improv import ImprovEvent
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper
from laughtrack.utilities.infrastructure.scraper.scraper import BatchScraper
from laughtrack.utilities.infrastructure.scraper.config import BatchScrapingConfig

from .data import ImprovPageData
from .extractor import ImprovExtractor
from .transformer import ImprovEventTransformer


class ImprovScraper(BaseScraper):
    """
    Multi-step scraper for improv.com venues.
    1. Discovers event links from the club's calendar page
    2. Scrapes each event page for JSON-LD event data

    Follows Pattern A: JSON-LD Scraper with multi-step URL discovery.
    """

    key = "improv"  # Must match club.scraper field

    # Configuration for parallel processing
    MAX_CONCURRENT_REQUESTS = 5  # Limit concurrent requests to be respectful
    REQUEST_DELAY = 0.5  # Delay between batches of requests in seconds

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(ImprovEventTransformer(club))
        # Use BaseHeaders for consistent mobile browser headers
        self.headers = BaseHeaders.get_venue_headers("improv", domain=club.scraping_url, referer=club.scraping_url)

    @staticmethod
    def _normalize_label(value: str) -> str:
        return "".join(ch for ch in value.lower() if ch.isalnum())

    def _expected_slug(self) -> str:
        url = self.club.scraping_url
        if "://" not in url:
            url = "https://" + url
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]
        return parts[0].lower() if parts else ""

    def _url_matches_current_club(self, url: str) -> bool:
        if not url:
            return False

        expected_slug = self._expected_slug()
        normalized_url = url.lower()
        if expected_slug and expected_slug in normalized_url:
            return True

        # Fallback for a few short TicketWeb codes like `hollyimprov` where the
        # full club name isn't present in the query params, but the path still is.
        normalized_name = self._normalize_label(self.club.name.replace("improv", ""))
        if normalized_name and normalized_name in self._normalize_label(url):
            return True

        return False

    def _event_matches_current_club(self, event: ImprovEvent) -> bool:
        location_name = (event.location_name or "").strip()
        if location_name:
            return self._normalize_label(location_name) == self._normalize_label(self.club.name)

        candidate_urls = [event.url] + [offer.get("url", "") for offer in (event.offers or [])]
        return any(self._url_matches_current_club(url) for url in candidate_urls)

    def _filter_cross_venue_events(self, events: List[ImprovEvent]) -> List[ImprovEvent]:
        kept: List[ImprovEvent] = []
        filtered = 0

        for event in events:
            if self._event_matches_current_club(event):
                kept.append(event)
                continue

            filtered += 1
            ticket_urls = [offer.get("url", "") for offer in (event.offers or []) if offer.get("url")]
            Logger.warning(
                f"{self._log_prefix}: Filtering cross-venue event '{event.name}' "
                f"(location='{event.location_name or ''}', event_url='{event.url}', "
                f"ticket_urls={ticket_urls[:2]})",
                self.logger_context,
            )

        if filtered:
            Logger.warning(
                f"{self._log_prefix}: Filtered {filtered} cross-venue event(s) before persistence",
                self.logger_context,
            )

        return kept

    async def get_data(self, url: str) -> Optional[ImprovPageData]:
        """
        Extract JSON-LD event data from an event page.
        """
        try:
            start_url = URLUtils.normalize_url(url)
            base_url = URLUtils.get_base_domain_with_protocol(start_url)
            # Follow "More Shows" style links across pages via async fetch_html + direct HTML parsing
            visited_urls = set()
            current_url = start_url
            all_ticket_links: List[str] = []
            seen_links = set()
            page_count = 0
            max_pages = 20  # safety cap

            while current_url and page_count < max_pages:
                visited_urls.add(current_url)

                html_content = await self.fetch_html(current_url)
                if not html_content:
                    break

                # Extract ticket links from this page
                page_ticket_links = ImprovExtractor.extract_ticket_links(
                    html_content,
                    base_url,
                    self.logger_context
                )

                if page_ticket_links:
                    # Deduplicate while preserving order
                    for link in page_ticket_links:
                        if link not in seen_links:
                            seen_links.add(link)
                            all_ticket_links.append(link)

                # Use only the explicit anchor id used by Improv sites
                next_url = HtmlScraper.get_link_url_by_id(html_content, anchor_id="moreshowsbtn", base_url=current_url)
                if not next_url or next_url in visited_urls:
                    break

                current_url = next_url
                page_count += 1

            if not all_ticket_links:
                Logger.warning(f"{self._log_prefix}: No ticket links found on {start_url}", self.logger_context)
                return None

            Logger.info(
                f"{self._log_prefix}: Found {len(all_ticket_links)} ticket links across {page_count + 1} page(s)",
                self.logger_context,
            )

            # Fetch HTML from each ticket URL in parallel to get complete event data
            batch_config = BatchScrapingConfig(
                max_concurrent=self.MAX_CONCURRENT_REQUESTS,
                delay_between_requests=self.REQUEST_DELAY,
                enable_logging=True,
            )
            batch = BatchScraper(self.logger_context, config=batch_config)

            async def process_ticket(link: str) -> List[ImprovEvent]:
                events = await self._process_single_ticket_url(link, base_url)
                if not events:
                    # Signal failure so BatchScraper counts it and omits from results
                    raise ValueError("No events extracted")
                return events

            raw_event_lists = await batch.process_batch(
                all_ticket_links,
                processor=process_ticket,
                description="improv ticket URLs",
            )

            # Flatten the list of lists into a single list of ImprovEvent
            event_list: List[ImprovEvent] = [event for sublist in raw_event_lists if sublist for event in sublist]
            event_list = self._filter_cross_venue_events(event_list)

            return ImprovPageData(event_list)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: Error extracting data from {url}: {e}", self.logger_context)
            return None

    async def _process_single_ticket_url(self, ticket_url: str, source_url: str) -> Optional[List[ImprovEvent]]:
        """
        Process a single ticket URL to extract event data.

        Args:
            ticket_url: Individual ticket purchase URL
            source_url: Original event page URL for logging context

        Returns:
            ImprovEvent object or None if processing fails
        """
        try:
            Logger.debug(f"{self._log_prefix}: Fetching ticket URL: {ticket_url}", self.logger_context)

            # Fetch HTML from the ticket URL
            ticket_url = URLUtils.normalize_url(ticket_url)
            ticket_html = await self.fetch_html(ticket_url)
            if not ticket_html:
                Logger.warning(f"{self._log_prefix}: Failed to fetch HTML from ticket URL: {ticket_url}", self.logger_context)
                return None

            # Process ticket URL through extractor (handles all extraction logic)
            return ImprovExtractor.process_ticket_url(ticket_html, ticket_url, self.logger_context)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: Error processing ticket URL {ticket_url}: {e}", self.logger_context)
            return None
