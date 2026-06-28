"""Standing Room Only event transformer for the SRO platform scraper."""

from laughtrack.core.entities.event.standing_room_only import StandingRoomOnlyEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class StandingRoomOnlyEventTransformer(DataTransformer[StandingRoomOnlyEvent]):
    """Transforms StandingRoomOnlyEvent objects into Show objects via event.to_show()."""

    pass
