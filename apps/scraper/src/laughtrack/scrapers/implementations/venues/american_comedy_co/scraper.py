"""
Generic Shopify scraper for comedy venues that sell tickets via Shopify.

Shopify stores expose a public JSON API at:

    https://{domain}/collections/{handle}/products.json?limit=250

Each product represents a show listing with variants for each date/time and
ticket tier. The scraper fetches the full product catalog from the collection
and parses variant titles for show dates and times.

DB setup:
    scraper      = 'shopify'
    scraping_url = 'https://americancomedyco.com/collections/shows'

A second Shopify venue can be onboarded with only a DB row — no Python changes.
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import ShopifyPageData
from .extractor import ShopifyExtractor
from .transformer import ShopifyEventTransformer


class ShopifyScraper(BaseScraper):
    """
    Generic Shopify scraper — reads club.scraping_url for the collection URL.

    The scraping_url should point to a Shopify collection page, e.g.:
        https://americancomedyco.com/collections/shows

    The scraper appends /products.json?limit=250 to fetch all products.
    """

    key = "shopify"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(ShopifyEventTransformer(club))

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Return the Shopify products.json API URL."""
        base_url = self.club.scraping_url.rstrip("/")
        return [f"{base_url}/products.json?limit=250"]

    async def get_data(self, url: str) -> Optional[ShopifyPageData]:
        """Fetch products from the Shopify API and return extracted events.

        Args:
            url: The Shopify products.json URL (from collect_scraping_targets)

        Returns:
            ShopifyPageData containing events, or None if no events found
        """
        try:
            await self.rate_limiter.await_if_needed(url)

            response = await self.fetch_json(url)
            if not response:
                Logger.info(f"{self._log_prefix}: no response from {url}", self.logger_context)
                return None

            timezone = self.club.timezone or "America/Los_Angeles"
            events = ShopifyExtractor.extract_events(response, timezone)

            if not events:
                Logger.info(f"{self._log_prefix}: no events found at {url}", self.logger_context)
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} events from {url}",
                self.logger_context,
            )
            return ShopifyPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching events from {url}: {e}",
                self.logger_context,
            )
            return None
