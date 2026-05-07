"""Event transformer for Dr. Grins Comedy Club."""

from laughtrack.core.entities.event.dr_grins import DrGrinsEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class DrGrinsEventTransformer(DataTransformer[DrGrinsEvent]):
    """Transforms DrGrinsEvent objects into Show domain objects."""
