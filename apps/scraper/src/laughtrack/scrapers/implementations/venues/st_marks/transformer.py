"""
St. Marks data transformer for converting TixrEvent objects to Show objects.
"""

from typing import List

from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class StMarksEventTransformer(DataTransformer[TixrEvent]):
    pass
