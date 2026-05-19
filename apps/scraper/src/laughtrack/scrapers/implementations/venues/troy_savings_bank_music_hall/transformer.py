"""Event transformer for Troy Savings Bank Music Hall."""

from laughtrack.core.entities.event.troy_savings_bank_music_hall import (
    TroySavingsBankMusicHallEvent,
)
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class TroySavingsBankMusicHallEventTransformer(
    DataTransformer[TroySavingsBankMusicHallEvent]
):
    """Transforms TroySavingsBankMusicHallEvent objects into Show objects."""
