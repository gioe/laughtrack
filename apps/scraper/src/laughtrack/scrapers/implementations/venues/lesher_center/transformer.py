"""Lesher Center event transformer."""

from laughtrack.core.entities.event.lesher_center import LesherCenterEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class LesherCenterTransformer(DataTransformer[LesherCenterEvent]):
    """Convert Lesher Center event instances to Show objects."""

    pass
