"""Transformer for SimpleTix events."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer
from laughtrack.core.entities.event.simpletix import SimpleTixEvent


class SimpleTixTransformer(DataTransformer[SimpleTixEvent]):
    pass
