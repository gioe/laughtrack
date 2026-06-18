"""
Generic WooCommerce Store API scraper.

Serves WordPress + WooCommerce venues that sell each show as a product and expose
the public Store API at ``{site}/wp-json/wc/store/v1/products``. Each product
carries "Show Dates" (MM/DD/YYYY) and "Show Times" attribute terms plus a
``permalink`` ticket URL; multi-date / multi-time products fan out into one show
per showtime.

Per-venue config is the club's ``source_url``: either the site root
(``https://grandcomedyclub.com``) or the products endpoint directly. The comedy
category defaults to "Comedy Events".

Venues served:
- Grand Comedy Club & Pizzeria (club 8897, grandcomedyclub.com)
"""

from typing import List, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import WoocommerceStoreApiPageData
from .extractor import WoocommerceStoreApiExtractor
from .transformer import WoocommerceStoreApiEventTransformer

_PRODUCTS_PATH = "/wp-json/wc/store/v1/products"
_PER_PAGE = 100
_MAX_PAGES = 10


class WoocommerceStoreApiScraper(BaseScraper):
    """Generic scraper for venues selling shows as WooCommerce Store API products."""

    key = "woocommerce_store_api"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(WoocommerceStoreApiEventTransformer(club))

    async def collect_scraping_targets(self) -> List[str]:
        """Return the WooCommerce products endpoint URL (per_page enforced)."""
        base = (self.club.scraping_url or "").strip()
        if not base:
            Logger.warn(f"{self._log_prefix}: club has no source_url", self.logger_context)
            return []

        parsed = urlparse(base)
        path = parsed.path or ""
        if _PRODUCTS_PATH not in path:
            path = path.rstrip("/") + _PRODUCTS_PATH

        params = parse_qs(parsed.query, keep_blank_values=True)
        params["per_page"] = [str(_PER_PAGE)]
        query = urlencode({k: v[0] for k, v in params.items()})
        return [urlunparse(parsed._replace(path=path, query=query))]

    async def get_data(self, url: str) -> Optional[WoocommerceStoreApiPageData]:
        """Fetch the products feed (paginating) and extract comedy showtimes."""
        try:
            events = []
            for page in range(1, _MAX_PAGES + 1):
                page_url = self._with_page(url, page)
                response = await self.fetch_json(page_url)
                if not isinstance(response, list) or not response:
                    break
                events.extend(WoocommerceStoreApiExtractor.extract_events(response))
                if len(response) < _PER_PAGE:
                    break
            else:
                Logger.warn(
                    f"{self._log_prefix}: reached MAX_PAGES ({_MAX_PAGES}) — pagination stopped early",
                    self.logger_context,
                )

            if not events:
                Logger.warn(f"{self._log_prefix}: no comedy showtimes extracted", self.logger_context)
                return None

            Logger.info(f"{self._log_prefix}: extracted {len(events)} showtimes", self.logger_context)
            return WoocommerceStoreApiPageData(event_list=events)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: error fetching products: {e}", self.logger_context)
            return None

    @staticmethod
    def _with_page(url: str, page: int) -> str:
        """Return ``url`` with the WooCommerce ``page`` query param set."""
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        params["page"] = [str(page)]
        query = urlencode({k: v[0] for k, v in params.items()})
        return urlunparse(parsed._replace(query=query))
