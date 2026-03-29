"""Vivenu event transformer."""

from laughtrack.core.entities.event.vivenu import VivenuEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class VivenuEventTransformer(DataTransformer[VivenuEvent]):
    pass
