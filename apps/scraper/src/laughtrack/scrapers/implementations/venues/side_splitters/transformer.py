"""Data transformer for Side Splitters Comedy Club events."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from .data import SideSplittersShow


class SideSplittersEventTransformer(DataTransformer[SideSplittersShow]):
    """Transforms SideSplittersShow objects into Show entities."""
