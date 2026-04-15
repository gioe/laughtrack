"""Off Cabot Comedy and Events event transformer."""

from laughtrack.core.entities.event.off_cabot import OffCabotEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class OffCabotEventTransformer(DataTransformer[OffCabotEvent]):
    """Transforms OffCabotEvent objects into Show objects via event.to_show()."""

    pass
