"""Ice House Comedy Club event transformer."""

from laughtrack.core.entities.event.ice_house import IceHouseEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class IceHouseEventTransformer(DataTransformer[IceHouseEvent]):
    pass
