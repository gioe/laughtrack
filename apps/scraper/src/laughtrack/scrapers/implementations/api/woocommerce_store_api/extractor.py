"""WooCommerce Store API event extraction.

Turns the ``/wp-json/wc/store/v1/products`` response (a top-level JSON array of
products) into ``WoocommerceEvent`` showtimes. Each product is filtered to the
comedy category, then its "Show Dates" x "Show Times" attribute terms are
expanded into one event per showtime.
"""

import html
from typing import Any, Dict, List, Optional

from laughtrack.core.entities.event.woocommerce import WoocommerceEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

# Attribute names carrying the per-show schedule on each product.
_SHOW_DATES_ATTR = "show dates"
_SHOW_TIMES_ATTR = "show times"

# Default category the comedy products live under. Matched case-insensitively
# against each product's category names and slugs.
_DEFAULT_COMEDY_CATEGORY = "comedy events"


class WoocommerceStoreApiExtractor:
    """Converts a WooCommerce Store API products array into WoocommerceEvent objects."""

    @staticmethod
    def extract_events(
        products: Any, comedy_category: str = _DEFAULT_COMEDY_CATEGORY
    ) -> List[WoocommerceEvent]:
        """Extract showtimes from the products feed, filtered to the comedy category."""
        if not isinstance(products, list):
            Logger.warn("WoocommerceStoreApiExtractor: products payload was not a list")
            return []

        category = comedy_category.strip().lower()
        events: List[WoocommerceEvent] = []
        for product in products:
            if not isinstance(product, dict):
                continue
            try:
                if not WoocommerceStoreApiExtractor._in_category(product, category):
                    continue
                events.extend(WoocommerceStoreApiExtractor._expand_product(product))
            except Exception as e:
                Logger.warn(f"WoocommerceStoreApiExtractor: skipping product due to error: {e}")
        return events

    @staticmethod
    def _in_category(product: Dict[str, Any], category: str) -> bool:
        """True when the product belongs to the target comedy category (name or slug)."""
        for cat in product.get("categories") or []:
            if not isinstance(cat, dict):
                continue
            name = (cat.get("name") or "").strip().lower()
            slug = (cat.get("slug") or "").strip().lower()
            if category in (name, slug) or category.replace(" ", "") == slug:
                return True
        return False

    @staticmethod
    def _expand_product(product: Dict[str, Any]) -> List[WoocommerceEvent]:
        """Expand one product into one WoocommerceEvent per (date, time) showtime."""
        attrs = WoocommerceStoreApiExtractor._attribute_terms(product)
        dates = attrs.get(_SHOW_DATES_ATTR, [])
        if not dates:
            return []
        times = attrs.get(_SHOW_TIMES_ATTR, []) or [None]

        name = html.unescape(product.get("name") or "").strip()
        permalink = product.get("permalink") or product.get("link") or ""
        price = WoocommerceStoreApiExtractor._parse_price(product)

        events: List[WoocommerceEvent] = []
        for date_str in dates:
            for time_str in times:
                events.append(
                    WoocommerceEvent(
                        name=name,
                        date_str=date_str,
                        time_str=time_str,
                        permalink=permalink,
                        price=price,
                    )
                )
        return events

    @staticmethod
    def _attribute_terms(product: Dict[str, Any]) -> Dict[str, List[str]]:
        """Map lower-cased attribute name -> list of its term names."""
        out: Dict[str, List[str]] = {}
        for attr in product.get("attributes") or []:
            if not isinstance(attr, dict):
                continue
            name = (attr.get("name") or "").strip().lower()
            terms = [
                (t.get("name") or "").strip()
                for t in attr.get("terms") or []
                if isinstance(t, dict) and (t.get("name") or "").strip()
            ]
            if name and terms:
                out[name] = terms
        return out

    @staticmethod
    def _parse_price(product: Dict[str, Any]) -> Optional[float]:
        """Parse the product price (WooCommerce reports minor units, e.g. cents)."""
        prices = product.get("prices")
        if not isinstance(prices, dict):
            return None
        raw = prices.get("price")
        if raw in (None, ""):
            return None
        try:
            minor_unit = int(prices.get("currency_minor_unit", 2))
            return int(raw) / (10 ** minor_unit)
        except (ValueError, TypeError):
            return None
