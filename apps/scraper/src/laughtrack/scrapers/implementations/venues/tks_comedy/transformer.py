"""Transformer for TK's events."""

from laughtrack.core.entities.event.tks_comedy import TksComedyEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class TksComedyEventTransformer(DataTransformer[TksComedyEvent]):
    """Transform TksComedyEvent objects via their ShowConvertible implementation."""
