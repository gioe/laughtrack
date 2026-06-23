"""Tugoz event transformer."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from .data import TugozEvent


class TugozEventTransformer(DataTransformer[TugozEvent]):
    """Transforms TugozEvent objects into Show objects."""

