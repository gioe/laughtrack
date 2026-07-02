"""Hennepin Arts event transformer."""

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.hennepin_arts import HennepinArtsEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class HennepinArtsEventTransformer(DataTransformer[HennepinArtsEvent]):
    """Convert Hennepin Arts events to Show objects."""

    def __init__(self, club: Club):
        self.club = club

    def transform(self, event: HennepinArtsEvent):
        return event.to_show(self.club)
