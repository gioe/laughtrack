"""Sunset Strip Comedy Club event transformer."""

from laughtrack.core.entities.event.squadup import SquadUpEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class SunsetStripEventTransformer(DataTransformer[SquadUpEvent]):
    pass
