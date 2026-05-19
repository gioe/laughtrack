"""Transformer for accesso ShoWare performance data."""

from laughtrack.core.entities.event.showare import ShoWarePerformance
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class ShoWareTransformer(DataTransformer[ShoWarePerformance]):
    """Transforms ShoWarePerformance rows into Show objects."""
