"""DICE event transformer."""

from laughtrack.core.entities.event.dice import DiceEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class DiceEventTransformer(DataTransformer[DiceEvent]):
    """Transforms DICE events into Show objects."""
