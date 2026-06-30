"""Transformer for Comix Roadhouse events."""

from laughtrack.core.entities.event.comix_roadhouse import ComixRoadhouseEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class ComixRoadhouseTransformer(DataTransformer[ComixRoadhouseEvent]):
    pass
