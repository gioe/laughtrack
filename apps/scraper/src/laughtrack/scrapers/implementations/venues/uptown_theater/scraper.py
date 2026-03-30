"""
Uptown Theater scraper for uptownpvd.com.

Uptown Theater uses a Next.js site that renders JSON-LD server-side.
The events listing page contains a CollectionPage JSON-LD with event URLs,
and each individual event page contains a ComedyEvent JSON-LD with full details.

Strategy:
1. Fetch the events listing page to extract event URLs from CollectionPage JSON-LD
2. Batch-fetch each event detail page and extract ComedyEvent JSON-LD
3. Transform via JsonLdTransformer
"""

from typing import List, Optional
from urllib.parse import urljoin

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.json.utils import JSONUtils
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor
from laughtrack.scrapers.implementations.json_ld.transformer import JsonLdTransformer
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper
from laughtrack.utilities.infrastructure.scraper.config import BatchScrapingConfig
from laughtrack.utilities.infrastructure.scraper.scraper import BatchScraper

from .data import UptownTheaterPageData


class UptownTheaterScraper(BaseScraper):
    """
    Multi-step scraper for Uptown Theater (uptownpvd.com).

    1. Fetches the events listing page and extracts event URLs from CollectionPage JSON-LD
    2. Fetches each event detail page and extracts ComedyEvent JSON-LD
    3. Transforms via JsonLdTransformer
    """

    key = "uptown_theater"

    MAX_CONCURRENT_REQUESTS = 5
    REQUEST_DELAY = 0.5

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(JsonLdTransformer(club))

    async def get_data(self, url: str) -> Optional[UptownTheaterPageData]:
        """
        Fetch the events listing page, discover event URLs, then scrape each event page.
        """
        try:
            listing_url = URLUtils.normalize_url(url)
            html = await self.fetch_html(listing_url)
            if not html:
                Logger.warn(f"{self._log_prefix}: Failed to fetch events listing page: {listing_url}", self.logger_context)
                return None

            event_urls = self._extract_event_urls(html, listing_url)
            if not event_urls:
                Logger.warn(f"{self._log_prefix}: No event URLs found on listing page: {listing_url}", self.logger_context)
                return None

            Logger.info(f"{self._log_prefix}: Found {len(event_urls)} event URLs on listing page", self.logger_context)

            batch_config = BatchScrapingConfig(
                max_concurrent=self.MAX_CONCURRENT_REQUESTS,
                delay_between_requests=self.REQUEST_DELAY,
                enable_logging=True,
            )
            batch = BatchScraper(self.logger_context, config=batch_config)

            async def process_event_url(event_url: str) -> List[JsonLdEvent]:
                events = await self._scrape_event_page(event_url)
                if not events:
                    raise ValueError("No events extracted")
                return events

            raw_event_lists = await batch.process_batch(
                event_urls,
                processor=process_event_url,
                description="Uptown Theater event pages",
            )

            event_list: List[JsonLdEvent] = [
                event for sublist in raw_event_lists if sublist for event in sublist
            ]

            if not event_list:
                Logger.warn(f"{self._log_prefix}: No events extracted from any event page", self.logger_context)
                return None

            return UptownTheaterPageData(event_list)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: Error scraping Uptown Theater listing: {e}", self.logger_context)
            return None

    def _extract_event_urls(self, html: str, listing_url: str) -> List[str]:
        """
        Extract event page URLs from the CollectionPage JSON-LD on the events listing page.

        The listing page embeds a CollectionPage with itemListElement entries,
        each having a 'url' field pointing to an individual event page.
        """
        try:
            script_contents = HtmlScraper.get_json_ld_script_contents(html)
            if not script_contents:
                return []

            json_objects = JSONUtils.parse_json_ld_contents(script_contents)
            if not json_objects:
                return []

            event_urls: List[str] = []
            found_collection_page = False
            for obj in json_objects:
                if obj.get("@type") != "CollectionPage":
                    continue
                found_collection_page = True
                main_entity = obj.get("mainEntity", {})
                if not isinstance(main_entity, dict):
                    continue
                items = main_entity.get("itemListElement", [])
                for item in items:
                    item_url = item.get("url", "")
                    if item_url:
                        # Resolve relative URLs against the listing page origin
                        event_urls.append(urljoin(listing_url, item_url))

            if not found_collection_page:
                types_found = [obj.get("@type") for obj in json_objects]
                Logger.warn(
                    f"{self._log_prefix}: No CollectionPage found in JSON-LD; @type values present: {types_found}",
                    self.logger_context,
                )

            return event_urls

        except Exception as e:
            Logger.error(f"{self._log_prefix}: Error extracting event URLs from listing page: {e}", self.logger_context)
            return []

    async def _scrape_event_page(self, event_url: str) -> Optional[List[JsonLdEvent]]:
        """Fetch a single event detail page and extract ComedyEvent JSON-LD."""
        try:
            normalized_url = URLUtils.normalize_url(event_url)
            html = await self.fetch_html(normalized_url)
            if not html:
                Logger.warn(f"{self._log_prefix}: Failed to fetch event page: {normalized_url}", self.logger_context)
                return None

            events = EventExtractor.extract_events(html)
            if not events:
                Logger.warn(f"{self._log_prefix}: No JSON-LD events found on event page: {normalized_url}", self.logger_context)
                return None

            return events

        except Exception as e:
            Logger.error(f"{self._log_prefix}: Error scraping event page {event_url}: {e}", self.logger_context)
            return None
