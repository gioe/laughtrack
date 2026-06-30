"""Transformer for Venetian entertainment events."""

from laughtrack.core.entities.event.venetian_entertainment import VenetianEntertainmentEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class VenetianEntertainmentTransformer(DataTransformer[VenetianEntertainmentEvent]):
    pass
