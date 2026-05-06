"""Data transformer for LAUGH IT UP COMEDY CLUB events."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from .data import LaughItUpComedyShow


class LaughItUpComedyEventTransformer(DataTransformer[LaughItUpComedyShow]):
    """Transforms LaughItUpComedyShow objects into Show entities."""
