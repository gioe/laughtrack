"""
Gotham Comedy Club scraper implementation using standardized project patterns.

This scraper handles Gotham Comedy Club's live events feed — a Cloudflare
Worker proxying the venue's Webflow CMS collection — which serves paginated
JSON pages of upcoming showtimes. The scraper fetches the feed pages and
transforms the data into Show objects.

This implementation follows the established architectural patterns:
- BaseScraper pipeline for standard workflow
- GothamEventExtractor: Handles feed JSON extraction and Showclix enrichment
- GothamEventTransformer: Transforms GothamFeedEvent objects to Show objects
- GothamPageData: Data model for extracted page data

Clean single-responsibility architecture:
- GothamEventExtractor: feed JSON API → GothamFeedEvent objects with enrichment
- GothamEventTransformer: GothamFeedEvent objects → Show objects
- GothamComedyClubScraper: Orchestrates the standard pipeline
"""

import math
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import ScrapingTarget
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .extractor import GothamEventExtractor
from .transformer import GothamEventTransformer

# Cloudflare Worker proxying the venue's Webflow CMS events collection.
FEED_BASE_URL = "https://square-mountain-7159.alex-cdc.workers.dev/items"

# The worker caps `limit` at 100 (requesting more echoes pagination.limit=100).
PAGE_SIZE = 100

# Defensive bound: the feed currently holds ~200 items (a few months of
# showtimes). 10 pages = 1,000 items of headroom while still bounding the
# scrape if pagination.total ever returns garbage.
MAX_PAGES = 10


class GothamComedyClubScraper(BaseScraper):
    """
    Gotham Comedy Club scraper using standardized project patterns.

    This implementation:
    1. Uses BaseScraper's standard pipeline (collect_scraping_targets → get_data → transform_data)
    2. Leverages built-in fetch methods with error handling and retries
    3. Follows established error handling and logging patterns
    4. Separates concerns: extraction vs transformation via dedicated classes
    """

    key = "gotham"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(GothamEventTransformer(club))
        self.extractor = GothamEventExtractor(club, self.get_session, proxy_pool=self.proxy_pool)

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """
        Paginate the live events feed into page URLs.

        Probes the feed with a minimal request to read pagination.total, then
        generates one target URL per page of PAGE_SIZE items, defensively
        bounded at MAX_PAGES.

        Returns:
            List of feed page URLs (e.g., .../items?limit=100&offset=0)
        """
        num_pages = await self._fetch_page_count()
        targets = [
            f"{FEED_BASE_URL}?limit={PAGE_SIZE}&offset={page * PAGE_SIZE}"
            for page in range(num_pages)
        ]

        Logger.info(
            f"{self._log_prefix}: generated {len(targets)} feed page URLs",
            self.logger_context,
        )

        return targets

    async def _fetch_page_count(self) -> int:
        """
        Probe the feed for pagination.total and derive the page count.

        Falls back to a single page when the probe fails or returns an
        unusable total, so a flaky probe degrades to a partial scrape
        instead of zero targets.

        Returns:
            Number of PAGE_SIZE pages to fetch (1..MAX_PAGES)
        """
        probe_url = f"{FEED_BASE_URL}?limit=1&offset=0"
        total = 0
        try:
            probe = await self.fetch_json(probe_url, headers=self.extractor.get_headers())
            if isinstance(probe, dict):
                pagination = probe.get("pagination") or {}
                total = int(pagination.get("total") or 0)
        except Exception as e:
            Logger.warn(
                f"{self._log_prefix}: feed pagination probe failed ({e}); defaulting to 1 page",
                self.logger_context,
            )

        if total <= 0:
            Logger.warn(
                f"{self._log_prefix}: feed reported no usable total (total={total}); defaulting to 1 page",
                self.logger_context,
            )
            return 1

        num_pages = math.ceil(total / PAGE_SIZE)
        if num_pages > MAX_PAGES:
            Logger.warn(
                f"{self._log_prefix}: feed total {total} exceeds defensive bound; "
                f"capping at {MAX_PAGES} pages ({MAX_PAGES * PAGE_SIZE} items)",
                self.logger_context,
            )
            num_pages = MAX_PAGES

        Logger.info(
            f"{self._log_prefix}: feed reports {total} items → {num_pages} page(s) of {PAGE_SIZE}",
            self.logger_context,
        )
        return num_pages

    async def get_data(self, target: ScrapingTarget) -> Optional[EventListContainer]:
        """
        Extract Gotham event data from one feed page using the dedicated extractor.

        Args:
            target: A feed page URL (e.g., .../items?limit=100&offset=0)

        Returns:
            GothamPageData containing the events data or None if the page had
            no upcoming events
        """
        return await self.extractor.extract_events(target)
