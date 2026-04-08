"""Event transformer for The Moon (Tallahassee)."""

from laughtrack.core.entities.event.the_moon import TheMoonEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class TheMoonEventTransformer(DataTransformer[TheMoonEvent]):
    """Transforms TheMoonEvent objects into Show domain objects."""
