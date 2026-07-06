"""WooCommerce Store API event extraction.

Turns the ``/wp-json/wc/store/v1/products`` response (a top-level JSON array of
products) into ``WoocommerceEvent`` showtimes. Each product is filtered to the
comedy category, then its "Show Dates" x "Show Times" attribute terms are
expanded into one event per showtime.
"""

import html
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from laughtrack.core.entities.event.woocommerce import WoocommerceEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

# Attribute names carrying the per-show schedule on each product.
_SHOW_DATES_ATTR = "show dates"
_SHOW_TIMES_ATTR = "show times"

# Default category the comedy products live under. Matched case-insensitively
# against each product's category names and slugs.
_DEFAULT_COMEDY_CATEGORY = "comedy events"

# Fallback schedule parse (e.g. Soul Joel's): venues that carry no
# "Show Dates"/"Show Times" attributes embed the date+time in the product
# description prose ("Friday August 7th at 7pm ..."). Year is absent and inferred
# to the next occurrence. Anchored on a weekday so it does not match the venue's
# street address ("50 SunnyBrook Road") elsewhere in the prose.
_DESC_SCHEDULE_RE = re.compile(
    r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\s+"
    r"([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?\s+at\s+"
    r"(\d{1,2}(?::\d{2})?\s*[ap]m)",
    re.IGNORECASE,
)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


class WoocommerceStoreApiExtractor:
    """Converts a WooCommerce Store API products array into WoocommerceEvent objects."""

    @staticmethod
    def extract_events(
        products: Any,
        comedy_category: str = _DEFAULT_COMEDY_CATEGORY,
        comedy_tags: Optional[List[str]] = None,
        now: Optional[datetime] = None,
    ) -> List[WoocommerceEvent]:
        """Extract showtimes from the products feed, filtered to comedy products.

        ``comedy_category`` matches each product's category name/slug. When
        ``comedy_tags`` is provided (a list of case-insensitive substrings), a
        product must additionally carry a matching tag — used for venues whose
        single ticket category mixes comedy with non-comedy events (podcasts,
        dance nights), so the tag narrows it to comedy. ``now`` seeds the
        year-inference for description-prose dates (defaults to the current time).
        """
        if not isinstance(products, list):
            Logger.warn("WoocommerceStoreApiExtractor: products payload was not a list")
            return []

        category = comedy_category.strip().lower()
        tag_filters = [t.strip().lower() for t in (comedy_tags or []) if t and t.strip()]
        events: List[WoocommerceEvent] = []
        for product in products:
            if not isinstance(product, dict):
                continue
            try:
                if not WoocommerceStoreApiExtractor._in_category(product, category):
                    continue
                if tag_filters and not WoocommerceStoreApiExtractor._has_comedy_tag(product, tag_filters):
                    continue
                events.extend(WoocommerceStoreApiExtractor._expand_product(product, now))
            except Exception as e:
                Logger.warn(f"WoocommerceStoreApiExtractor: skipping product due to error: {e}")
        return events

    @staticmethod
    def _has_comedy_tag(product: Dict[str, Any], tag_filters: List[str]) -> bool:
        """True when any product tag name/slug contains one of the comedy substrings."""
        for tag in product.get("tags") or []:
            if not isinstance(tag, dict):
                continue
            haystack = f"{(tag.get('name') or '').lower()} {(tag.get('slug') or '').lower()}"
            if any(sub in haystack for sub in tag_filters):
                return True
        return False

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
    def _expand_product(
        product: Dict[str, Any], now: Optional[datetime] = None
    ) -> List[WoocommerceEvent]:
        """Expand one product into one WoocommerceEvent per showtime.

        Prefers the structured "Show Dates" x "Show Times" attributes; when a
        product carries neither, falls back to parsing date+time out of the
        product description prose.
        """
        name = html.unescape(product.get("name") or "").strip()
        permalink = product.get("permalink") or product.get("link") or ""
        price = WoocommerceStoreApiExtractor._parse_price(product)

        attrs = WoocommerceStoreApiExtractor._attribute_terms(product)
        dates = attrs.get(_SHOW_DATES_ATTR, [])
        if dates:
            times = attrs.get(_SHOW_TIMES_ATTR, []) or [None]
            schedule: List[Tuple[str, Optional[str]]] = [
                (date_str, time_str) for date_str in dates for time_str in times
            ]
        else:
            schedule = WoocommerceStoreApiExtractor._schedule_from_description(
                product.get("description") or "", now
            )

        return [
            WoocommerceEvent(
                name=name,
                date_str=date_str,
                time_str=time_str,
                permalink=permalink,
                price=price,
            )
            for date_str, time_str in schedule
        ]

    @staticmethod
    def _schedule_from_description(
        description: str, now: Optional[datetime] = None
    ) -> List[Tuple[str, str]]:
        """Parse "<Weekday> <Month> <Day> at <time>" schedules from description HTML.

        Returns ``(MM/DD/YYYY, time)`` pairs (the format WoocommerceEvent parses),
        inferring the year as the next occurrence relative to ``now``. Deduplicates
        repeated matches within one description.
        """
        text = _HTML_TAG_RE.sub(" ", html.unescape(description or ""))
        reference = now or datetime.now()
        seen: set = set()
        schedule: List[Tuple[str, str]] = []
        for match in _DESC_SCHEDULE_RE.finditer(text):
            month_word, day_str, time_str = match.group(1), match.group(2), match.group(3)
            try:
                month = datetime.strptime(month_word[:3], "%b").month
            except ValueError:
                continue
            day = int(day_str)
            year = reference.year
            if (month, day) < (reference.month, reference.day):
                year += 1
            date_str = f"{month:02d}/{day:02d}/{year}"
            time_norm = " ".join(time_str.split())
            key = (date_str, time_norm)
            if key in seen:
                continue
            seen.add(key)
            schedule.append((date_str, time_norm))
        return schedule

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
