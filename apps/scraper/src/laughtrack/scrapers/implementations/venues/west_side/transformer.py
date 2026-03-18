"""Data transformer for West Side Comedy Club events."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from .extractor import WestSideShow


class WestSideEventTransformer(DataTransformer[WestSideShow]):
    """Transforms WestSideShow objects into Show entities."""
