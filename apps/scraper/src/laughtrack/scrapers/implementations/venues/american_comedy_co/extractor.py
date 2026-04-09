"""Shopify product extraction — converts products.json response into ShopifyEvents.

Each Shopify product represents a show listing. Products may have multiple
variants representing different date/times (e.g. 7pm and 9pm shows) or
ticket tiers (General Admission, VIP). The extractor groups variants by
date/time and creates one ShopifyEvent per unique showtime.
"""

from typing import Any, Dict, List

from laughtrack.core.entities.event.shopify import ShopifyEvent, _parse_variant_datetime
from laughtrack.foundation.infrastructure.logger.logger import Logger


class ShopifyExtractor:
    """Converts raw Shopify products.json into ShopifyEvent objects."""

    @staticmethod
    def extract_events(
        api_response: Dict[str, Any], timezone: str = "America/Los_Angeles"
    ) -> List[ShopifyEvent]:
        """Extract ShopifyEvent objects from the products.json response.

        Groups variants by date/time — one ShopifyEvent per unique showtime.
        Uses the lowest price among variants sharing the same showtime.
        """
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

        # Get first image URL
        images = product.get("images") or []
        image_url = images[0].get("src", "") if images else ""

        variants = product.get("variants") or []
        if not variants:
            return []

        # Group variants by date/time
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
                # Keep lowest price and OR the availability
                existing = showtime_map[dt_key]
                if float(price) < float(existing["price"]):
                    existing["price"] = price
                existing["available"] = existing["available"] or available

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
