"""
The Stand NYC data transformation utilities.

This module provides utilities for transforming TixrEvent objects
into Show objects, implementing the DataTransformer interface.
"""

from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class TheStandEventTransformer(DataTransformer[TixrEvent]):
    pass