"""Page data container for the generic WooCommerce Store API scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.woocommerce import WoocommerceEvent


@dataclass
class WoocommerceStoreApiPageData:
    """Raw extracted showtimes from a WooCommerce Store API products feed."""

    event_list: List[WoocommerceEvent]
