"""Wix Events event transformer for the generic platform scraper."""

from laughtrack.core.entities.event.wix_events import WixEventsEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from .routing import WixVenueRouter


class WixEventsEventTransformer(DataTransformer[WixEventsEvent]):
    """Transforms WixEventsEvent objects into Show objects via event.to_show()."""

    def __init__(self, club, router=None):
        super().__init__(club)
        self.router = router or WixVenueRouter(club)

    def transform_to_show(self, raw_data):
        if not self.router.enabled:
            return super().transform_to_show(raw_data)
        return self.router.convert(raw_data)
