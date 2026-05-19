"""Fox Tucson Theatre event transformer."""

from laughtrack.core.entities.event.fox_tucson_theatre import FoxTucsonTheatreEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class FoxTucsonTheatreTransformer(DataTransformer[FoxTucsonTheatreEvent]):
    """Convert Fox Tucson event cards to Show objects."""

    pass
