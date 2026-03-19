"""Data transformer for Comedy Key West events."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from .data import ComedyKeyWestShow


class ComedyKeyWestEventTransformer(DataTransformer[ComedyKeyWestShow]):
    """Transforms ComedyKeyWestShow objects into Show entities."""
