"""Grove34 event transformer for converting Grove34Event objects to Show objects."""

from typing import List, Optional

from laughtrack.core.entities.event.grove34 import Grove34Event
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class Grove34EventTransformer(DataTransformer[Grove34Event]):
    pass
