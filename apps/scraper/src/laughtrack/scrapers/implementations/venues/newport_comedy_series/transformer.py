"""Data transformer for Newport Comedy Series events."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from .extractor import NewportComedySeriesShow


class NewportComedySeriesEventTransformer(DataTransformer[NewportComedySeriesShow]):
    """Transforms NewportComedySeriesShow objects into Show entities."""
