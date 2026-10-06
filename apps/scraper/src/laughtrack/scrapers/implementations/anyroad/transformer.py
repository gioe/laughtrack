"""AnyRoad event -> Show transformer.

Legacy sources preserve their free-text ``locationInfo`` as ``Show.room``.
Sources opting into reviewed physical routing resolve the destination before
conversion, retaining native room text and producer ownership. Never use room
text as an inferred physical address or manufacture performance identity.
"""

from typing import Optional

from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class AnyRoadTransformer(DataTransformer[JsonLdEvent]):
    def __init__(self, club, venue_router=None):
        super().__init__(club)
        self.venue_router = venue_router

    def transform_to_show(self, raw_data: ShowConvertible) -> Optional[Show]:
        if self.venue_router is not None and self.venue_router.enabled:
            return self.venue_router.convert(raw_data)
        show = super().transform_to_show(raw_data)
        if show is None:
            return None
        location = getattr(raw_data, "location", None)
        room = getattr(location, "name", "") if location else ""
        if room:
            show.room = room.strip()
        return show
