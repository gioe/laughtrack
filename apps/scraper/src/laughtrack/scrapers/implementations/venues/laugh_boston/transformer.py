"""Laugh Boston data transformation utilities."""

from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class LaughBostonEventTransformer(DataTransformer[TixrEvent]):
    pass
