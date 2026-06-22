"""Dreamland event transformer (pass-through to DreamlandEvent.to_show)."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from .data import DreamlandEvent


class DreamlandEventTransformer(DataTransformer[DreamlandEvent]):
    pass
