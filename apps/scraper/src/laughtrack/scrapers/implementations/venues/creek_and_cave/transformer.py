"""Creek and Cave event transformer."""

from laughtrack.core.entities.event.creek_and_cave import CreekAndCaveEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class CreekAndCaveEventTransformer(DataTransformer[CreekAndCaveEvent]):
    """
    Transformer for converting CreekAndCaveEvent objects to Show objects.

    Delegates to CreekAndCaveEvent.to_show() via the DataTransformer base class.
    """

    pass
