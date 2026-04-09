"""Data model for scraped page data from a Shopify-based comedy venue."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.shopify import ShopifyEvent


@dataclass
class ShopifyPageData:
    """Raw extracted event data from Shopify products.json API."""

    event_list: List[ShopifyEvent]
