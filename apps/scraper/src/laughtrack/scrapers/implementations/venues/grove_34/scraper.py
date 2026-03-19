"""
Grove34 specialized scraper for the Webflow site.

Grove 34 migrated from Wix to Webflow. Events are listed on the homepage
(grove34.com/) as HTML items with pagination. Each show has a detail page
at /shows/<slug> that contains a JSON-LD Event block with structured data.

Scraping strategy:
1. collect_scraping_targets(): fetch listing page(s), extract show detail URLs
2. get_data(show_url): fetch each show detail page, extract JSON-LD event
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.foundation.models.types import ScrapingTarget

from .data import Grove34PageData
from .extractor import Grove34EventExtractor
from .transformer import Grove34EventTransformer


class Grove34Scraper(BaseScraper):
    """
    Specialized scraper for grove34.com (Webflow CMS site).

    Discovers show URLs from the paginated listing page, then fetches
    each show's detail page to extract JSON-LD event data.
    """

    key = "grove34"
    _MAX_LISTING_PAGES = 20

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(Grove34EventTransformer(club))

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """
        Fetch the Grove34 listing page(s) and return all show detail URLs.

        Follows pagination (up to _MAX_LISTING_PAGES) to collect every show URL.
        """
        listing_url: Optional[str] = URLUtils.normalize_url(self.club.scraping_url)
        all_urls: List[str] = []
        seen: set = set()
        visited_listing_urls: set = set()
        pages_fetched = 0

        while listing_url and pages_fetched < self._MAX_LISTING_PAGES:
            if listing_url in visited_listing_urls:
                break
            visited_listing_urls.add(listing_url)
            try:
                await self.rate_limiter.await_if_needed(listing_url)
                html = await self.fetch_html_bare(listing_url)
                page_urls = Grove34EventExtractor.extract_show_urls(html)
                for url in page_urls:
                    if url not in seen:
                        seen.add(url)
                        all_urls.append(url)

                listing_url = Grove34EventExtractor.get_next_page_url(html, listing_url)
                pages_fetched += 1
            except Exception as e:
                Logger.error(f"Error fetching Grove34 listing page {listing_url}: {e}", self.logger_context)
                break

        Logger.info(f"Discovered {len(all_urls)} Grove34 show URLs across {pages_fetched} listing page(s)", self.logger_context)
        return all_urls

    async def get_data(self, url: ScrapingTarget) -> Optional[Grove34PageData]:
        """
        Fetch a show detail page and extract the Grove34Event from its JSON-LD.

        Args:
            url: Show detail page URL (e.g. https://grove34.com/shows/jazz-joints)

        Returns:
            Grove34PageData containing the single extracted event, or None
        """
        try:
            normalized_url = URLUtils.normalize_url(url)
            html = await self.fetch_html_bare(normalized_url)
            event = Grove34EventExtractor.extract_event(html, normalized_url)

            if not event:
                Logger.warning(f"No event extracted from {url}", self.logger_context)
                return None

            return Grove34PageData([event])

        except Exception as e:
            Logger.error(f"Error extracting data from {url}: {e}", self.logger_context)
            return None
