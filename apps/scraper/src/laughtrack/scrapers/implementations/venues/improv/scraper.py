"""
Improv multi-step scraper for improv.com venues.

This scraper discovers event links from the club's calendar page, then scrapes each event page for JSON-LD event data.
Follows the standardized 5-component architecture pattern.
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.core.entities.event.improv import ImprovEvent
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.utilities.infrastructure.paginator import Paginator
from laughtrack.utilities.infrastructure.scraper.scraper import BatchScraper
from laughtrack.utilities.infrastructure.scraper.config import BatchScrapingConfig

from .data import ImprovPageData
from .extractor import ImprovExtractor


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
        # Use BaseHeaders for consistent mobile browser headers
        self.headers = BaseHeaders.get_venue_headers("improv", domain=club.scraping_url, referer=club.scraping_url)

    async def get_data(self, url: str) -> Optional[ImprovPageData]:
        """
        Extract JSON-LD event data from an event page.
        """
        try:
            start_url = URLUtils.normalize_url(url)
            base_url = URLUtils.get_base_domain_with_protocol(start_url)
            # Use paginator to follow "More Shows" style links across pages
            paginator = Paginator()
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
                next_url = paginator.get_url_by_anchor_id(html_content, current_url, anchor_id="moreshowsbtn")
                if not next_url or next_url in visited_urls:
                    break

                current_url = next_url
                page_count += 1

            if not all_ticket_links:
                Logger.warning(f"No ticket links found on {start_url}", self.logger_context)
                return None

            Logger.info(
                f"Found {len(all_ticket_links)} ticket links across {page_count + 1} page(s)",
                self.logger_context,
            )

            # Fetch HTML from each ticket URL in parallel to get complete event data
            batch_config = BatchScrapingConfig(
                max_concurrent=self.MAX_CONCURRENT_REQUESTS,
                delay_between_requests=self.REQUEST_DELAY,
                enable_logging=True,
            )
            batch = BatchScraper(self.logger_context, config=batch_config)

            async def process_ticket(link: str) -> List[JsonLdEvent]:
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

            # Flatten the list of lists into a single list of JsonLdEvent
            event_list: List[JsonLdEvent] = [event for sublist in raw_event_lists if sublist for event in sublist]

            return ImprovPageData(event_list)

        except Exception as e:
            Logger.error(f"Error extracting data from {url}: {e}", self.logger_context)
            return None

    async def _process_single_ticket_url(self, ticket_url: str, source_url: str) -> Optional[List[JsonLdEvent]]:
        """
        Process a single ticket URL to extract event data.

        Args:
            ticket_url: Individual ticket purchase URL
            source_url: Original event page URL for logging context

        Returns:
            ImprovEvent object or None if processing fails
        """
        try:
            Logger.debug(f"Fetching ticket URL: {ticket_url}", self.logger_context)

            # Fetch HTML from the ticket URL
            ticket_url = URLUtils.normalize_url(ticket_url)
            ticket_html = await self.fetch_html(ticket_url)
            if not ticket_html:
                Logger.warning(f"Failed to fetch HTML from ticket URL: {ticket_url}", self.logger_context)
                return None

            # Process ticket URL through extractor (handles all extraction logic)
            return ImprovExtractor.process_ticket_url(ticket_html, ticket_url, self.logger_context)

        except Exception as e:
            Logger.error(f"Error processing ticket URL {ticket_url}: {e}", self.logger_context)
            return None