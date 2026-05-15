"""Event transformer for Barclays Center."""

from laughtrack.core.entities.event.barclays_center import BarclaysCenterEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class BarclaysCenterEventTransformer(DataTransformer[BarclaysCenterEvent]):
    """Transforms BarclaysCenterEvent objects into Show objects."""
