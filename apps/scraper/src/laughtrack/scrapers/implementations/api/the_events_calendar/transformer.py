"""Transformer for The Events Calendar (Tribe) events."""

from laughtrack.core.entities.event.tribe_events import TribeEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class TribeEventTransformer(DataTransformer[TribeEvent]):
    pass
