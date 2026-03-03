"""Grove34 event transformer for converting Grove34Event objects to Show objects."""

from laughtrack.core.entities.event.improv import ImprovEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class ImprovEventTransformer(DataTransformer[ImprovEvent]):
    pass
