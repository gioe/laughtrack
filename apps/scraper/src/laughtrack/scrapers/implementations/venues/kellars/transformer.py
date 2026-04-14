"""Event transformer for Kellar's: Modern Magic and Comedy Club."""

from laughtrack.core.entities.event.kellars import KellarsEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class KellarsEventTransformer(DataTransformer[KellarsEvent]):
    """Transforms KellarsEvent objects into Show domain objects."""
