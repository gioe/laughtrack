"""Palm Beach Improv event transformer."""

from laughtrack.core.entities.event.palm_beach_improv import PalmBeachImprovEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class PalmBeachImprovEventTransformer(DataTransformer[PalmBeachImprovEvent]):
    """Transforms PalmBeachImprovEvent objects into Show objects."""
