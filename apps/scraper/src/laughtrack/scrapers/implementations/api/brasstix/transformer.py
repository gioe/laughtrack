"""Transformer for BrassTix calendar events."""

from laughtrack.core.entities.event.brasstix import BrassTixEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class BrassTixTransformer(DataTransformer[BrassTixEvent]):
    """Transforms BrassTixEvent rows into Show objects."""
