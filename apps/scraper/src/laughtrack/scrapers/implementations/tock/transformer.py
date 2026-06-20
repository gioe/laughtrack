"""Tock event -> Show transformer."""

from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class TockTransformer(DataTransformer[JsonLdEvent]):
    pass

