"""Ninkashi event transformer."""

from laughtrack.core.entities.event.ninkashi import NinkashiEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class NinkashiEventTransformer(DataTransformer[NinkashiEvent]):
    pass
