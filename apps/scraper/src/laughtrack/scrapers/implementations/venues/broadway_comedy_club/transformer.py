"""
Broadway Comedy Club data transformation utilities.

This module provides utilities for transforming BroadwayEvent objects
into Show objects, implementing the DataTransformer interface.
"""

from laughtrack.core.entities.event.broadway import BroadwayEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class BroadwayEventTransformer(DataTransformer[BroadwayEvent]):
    pass
