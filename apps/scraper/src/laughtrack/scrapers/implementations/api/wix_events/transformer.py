"""Wix Events event transformer for the generic platform scraper."""

from laughtrack.core.entities.event.wix_events import WixEventsEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class WixEventsEventTransformer(DataTransformer[WixEventsEvent]):
    """Transforms WixEventsEvent objects into Show objects via event.to_show()."""

    pass
