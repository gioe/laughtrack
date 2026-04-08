"""Revolution Hall event transformer."""

from laughtrack.core.entities.event.revolution_hall import RevolutionHallEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class RevolutionHallEventTransformer(DataTransformer[RevolutionHallEvent]):
    """Transforms RevolutionHallEvent objects into Show objects via event.to_show()."""

    pass
