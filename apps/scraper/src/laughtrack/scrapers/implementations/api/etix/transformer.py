"""Event transformer for Etix venues."""

from laughtrack.core.entities.event.etix import EtixEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class EtixEventTransformer(DataTransformer[EtixEvent]):
    """Transforms EtixEvent objects into Show domain objects."""
