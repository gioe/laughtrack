"""Shopify event transformer."""

from laughtrack.core.entities.event.shopify import ShopifyEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class ShopifyEventTransformer(DataTransformer[ShopifyEvent]):
    pass
