"""Squarespace event transformer."""

from laughtrack.core.entities.event.squarespace import SquarespaceEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class SquarespaceEventTransformer(DataTransformer[SquarespaceEvent]):
    pass
