"""The Nest Theatre event transformer."""

from laughtrack.core.entities.event.nest_theatre import NestTheatreEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class NestTheatreEventTransformer(DataTransformer[NestTheatreEvent]):
    """Converts NestTheatreEvent objects to Show objects via NestTheatreEvent.to_show()."""

    pass
