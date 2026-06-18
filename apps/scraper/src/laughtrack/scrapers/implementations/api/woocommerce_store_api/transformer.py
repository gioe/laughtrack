"""WooCommerce Store API event transformer for the generic platform scraper."""

from laughtrack.core.entities.event.woocommerce import WoocommerceEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class WoocommerceStoreApiEventTransformer(DataTransformer[WoocommerceEvent]):
    """Transforms WoocommerceEvent objects into Show objects via event.to_show()."""

    pass
