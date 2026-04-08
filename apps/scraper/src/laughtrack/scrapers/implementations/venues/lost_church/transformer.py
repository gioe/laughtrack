"""The Lost Church event transformer."""

from laughtrack.core.entities.event.lost_church import LostChurchEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class LostChurchEventTransformer(DataTransformer[LostChurchEvent]):
    pass
