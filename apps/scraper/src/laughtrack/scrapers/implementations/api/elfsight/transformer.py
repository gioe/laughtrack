"""Elfsight Event Calendar event transformer."""

from laughtrack.core.entities.event.elfsight import ElfsightEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class ElfsightEventTransformer(DataTransformer[ElfsightEvent]):
    pass
