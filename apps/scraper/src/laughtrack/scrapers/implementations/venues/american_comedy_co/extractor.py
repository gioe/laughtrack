"""Shopify product extraction — converts products.json response into ShopifyEvents.

Each Shopify product represents a show listing. Two layout conventions exist:

  Format A (variant-date): Each variant title contains a date/time and ticket tier.
      Multiple variants may share a product (one per showtime × tier combo).
      The extractor groups variants by date/time → one ShopifyEvent per showtime.

  Format B (title-date): The product title itself contains the date/time and
      comedian lineup. Variants are ticket tiers only ("General Admission", "VIP").
      One ShopifyEvent per product, using the lowest variant price.

The extractor tries Format A first; if no variant yields a parseable date it
falls back to Format B.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from laughtrack.core.entities.event.shopify import (
    ShopifyEvent,
    parse_clock_time,
    parse_handle_title_date,
    parse_product_title_datetime,
    parse_variant_datetime,
)
from laughtrack.foundation.infrastructure.logger.logger import Logger

# Tags that mark a Shopify product as a non-show (classes, workshops, merch,
# memberships) — excluded from the show calendar regardless of date format.
# Word-boundary anchored so substrings of real show tags ("classic comedy",
# "masterclass", "merchandising night") are not swept up.
_NON_SHOW_TAG_RE = re.compile(r"\b(?:class|classes|merch|membership)\b", re.IGNORECASE)


class ShopifyExtractor:
    """Converts raw Shopify products.json into ShopifyEvent objects."""

    @staticmethod
    def extract_events(
        api_response: Dict[str, Any],
        timezone: str = "America/Los_Angeles",
        default_time: Optional[Tuple[int, int]] = None,
    ) -> List[ShopifyEvent]:
        """Extract ShopifyEvent objects from the products.json response.

        ``default_time`` is an opt-in ``(hour, minute)`` fallback applied only on
        the Format C path: a product that carries a parseable date but no clock
        time anywhere (title, variant, body) would otherwise be dropped. Venues
        that publish dates without times (ad-hoc Shopify stores whose showtime
        lives only on a flyer image) set ``default_show_time`` in metadata to
        keep these dated shows. ``None`` preserves the original drop behavior, so
        existing timed venues are unaffected.
        """
        products = api_response.get("products", [])
        if not isinstance(products, list):
            return []

        events: List[ShopifyEvent] = []
        for product in products:
            try:
                product_events = ShopifyExtractor._parse_product(
                    product, timezone, default_time
                )
                events.extend(product_events)
            except Exception as e:
                title = product.get("title", "unknown")
                Logger.warn(f"ShopifyExtractor: skipping product '{title}': {e}")
        return events

    @staticmethod
    def _parse_product(
        product: Dict[str, Any],
        timezone: str,
        default_time: Optional[Tuple[int, int]] = None,
    ) -> List[ShopifyEvent]:
        """Parse a single Shopify product into one or more ShopifyEvents."""
        product_id = product.get("id", 0)
        title = (product.get("title") or "").strip()
        handle = product.get("handle", "")
        body_html = product.get("body_html") or ""
        tags = product.get("tags") or []

        if not title or not handle:
            return []

        # Drop non-show products (classes, workshops, merch, memberships).
        tag_list = tags if isinstance(tags, list) else []
        if any(_NON_SHOW_TAG_RE.search(str(t)) for t in tag_list):
            return []

        images = product.get("images") or []
        image_url = images[0].get("src", "") if images else ""

        variants = product.get("variants") or []
        if not variants:
            return []

        # --- Format A: group variants by date/time ---
        showtime_map: Dict[str, Dict[str, Any]] = {}
        for variant in variants:
            variant_title = variant.get("title", "")
            dt = parse_variant_datetime(variant_title, timezone)
            if not dt:
                continue

            dt_key = dt.isoformat()
            price = variant.get("price", "0.00")
            available = variant.get("available", False)

            if dt_key not in showtime_map:
                showtime_map[dt_key] = {
                    "datetime": dt,
                    "price": price,
                    "available": available,
                }
            else:
                existing = showtime_map[dt_key]
                if float(price) < float(existing["price"]):
                    existing["price"] = price
                existing["available"] = existing["available"] or available

        if showtime_map:
            return [
                ShopifyEvent(
                    product_id=product_id,
                    title=title,
                    handle=handle,
                    show_date=info["datetime"],
                    price=info["price"],
                    available=info["available"],
                    image_url=image_url,
                    body_html=body_html,
                    timezone=timezone,
                    tags=tags if isinstance(tags, list) else [],
                )
                for info in showtime_map.values()
            ]

        # --- Format B: date/time in product title, variants are ticket tiers ---
        dt = parse_product_title_datetime(title, timezone)
        if dt:
            lowest_price, any_available = ShopifyExtractor._tier_summary(variants)
            return [
                ShopifyEvent(
                    product_id=product_id,
                    title=title,
                    handle=handle,
                    show_date=dt,
                    price=lowest_price,
                    available=any_available,
                    image_url=image_url,
                    body_html=body_html,
                    timezone=timezone,
                    tags=tag_list,
                )
            ]

        # --- Format C: date in the handle / numeric "M/D" title; time in the
        # title ("6/26 7pm") or in per-showtime variant titles ("6pm - <act>").
        return ShopifyExtractor._parse_format_c(
            product_id, title, handle, image_url, body_html, tag_list, variants,
            timezone, default_time,
        )

    @staticmethod
    def _tier_summary(variants: List[Dict[str, Any]]) -> tuple:
        """Return (lowest_price, any_available) across ticket-tier variants."""
        lowest_price = "0.00"
        any_available = False
        for variant in variants:
            price = variant.get("price", "0.00")
            if lowest_price == "0.00" or float(price) < float(lowest_price):
                lowest_price = price
            if variant.get("available", False):
                any_available = True
        return lowest_price, any_available

    @staticmethod
    def _parse_format_c(
        product_id: int,
        title: str,
        handle: str,
        image_url: str,
        body_html: str,
        tag_list: List[str],
        variants: List[Dict[str, Any]],
        timezone: str,
        default_time: Optional[Tuple[int, int]] = None,
    ) -> List[ShopifyEvent]:
        """Build events from a handle/numeric-title date plus a showtime.

        Emits one event per variant that carries its own clock time (e.g.
        "6pm - <act>", "7pm - <act>"); when no variant has a time, falls back to
        the time embedded in the product title, then to ``default_time`` (the
        opt-in ``default_show_time`` metadata) when the product carries a date
        but no time at all.
        """
        event_date = parse_handle_title_date(handle, title, timezone)
        if not event_date:
            return []

        events: List[ShopifyEvent] = []
        for variant in variants:
            clock = parse_clock_time(variant.get("title", ""))
            if not clock:
                continue
            show_dt = event_date.replace(hour=clock[0], minute=clock[1])
            events.append(
                ShopifyEvent(
                    product_id=product_id,
                    title=title,
                    handle=handle,
                    show_date=show_dt,
                    price=variant.get("price", "0.00"),
                    available=variant.get("available", False),
                    image_url=image_url,
                    body_html=body_html,
                    timezone=timezone,
                    tags=tag_list,
                )
            )
        if events:
            return events

        # No per-variant times — take the time from the product title, then fall
        # back to the opt-in default_time for date-only venues.
        clock = parse_clock_time(title) or default_time
        if not clock:
            return []
        show_dt = event_date.replace(hour=clock[0], minute=clock[1])
        lowest_price, any_available = ShopifyExtractor._tier_summary(variants)
        return [
            ShopifyEvent(
                product_id=product_id,
                title=title,
                handle=handle,
                show_date=show_dt,
                price=lowest_price,
                available=any_available,
                image_url=image_url,
                body_html=body_html,
                timezone=timezone,
                tags=tag_list,
            )
        ]
