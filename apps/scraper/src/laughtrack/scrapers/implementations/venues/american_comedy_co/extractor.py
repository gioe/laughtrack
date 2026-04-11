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

from typing import Any, Dict, List

from laughtrack.core.entities.event.shopify import (
    ShopifyEvent,
    _parse_product_title_datetime,
    _parse_variant_datetime,
)
from laughtrack.foundation.infrastructure.logger.logger import Logger


class ShopifyExtractor:
    """Converts raw Shopify products.json into ShopifyEvent objects."""

    @staticmethod
    def extract_events(
        api_response: Dict[str, Any], timezone: str = "America/Los_Angeles"
    ) -> List[ShopifyEvent]:
        """Extract ShopifyEvent objects from the products.json response."""
        products = api_response.get("products", [])
        if not isinstance(products, list):
            return []

        events: List[ShopifyEvent] = []
        for product in products:
            try:
                product_events = ShopifyExtractor._parse_product(product, timezone)
                events.extend(product_events)
            except Exception as e:
                title = product.get("title", "unknown")
                Logger.warn(f"ShopifyExtractor: skipping product '{title}': {e}")
        return events

    @staticmethod
    def _parse_product(
        product: Dict[str, Any], timezone: str
    ) -> List[ShopifyEvent]:
        """Parse a single Shopify product into one or more ShopifyEvents."""
        product_id = product.get("id", 0)
        title = (product.get("title") or "").strip()
        handle = product.get("handle", "")
        body_html = product.get("body_html") or ""
        tags = product.get("tags") or []

        if not title or not handle:
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
            dt = _parse_variant_datetime(variant_title, timezone)
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
        dt = _parse_product_title_datetime(title, timezone)
        if not dt:
            return []

        # Lowest price / any available across all tier variants
        lowest_price = "0.00"
        any_available = False
        for variant in variants:
            price = variant.get("price", "0.00")
            if lowest_price == "0.00" or float(price) < float(lowest_price):
                lowest_price = price
            if variant.get("available", False):
                any_available = True

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
                tags=tags if isinstance(tags, list) else [],
            )
        ]
