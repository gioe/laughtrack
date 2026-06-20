"""Ludus event -> Show transformer.

Each LudusEvent implements ShowConvertible.to_show, so the default
DataTransformer behavior is sufficient.
"""

from laughtrack.core.entities.event.ludus import LudusEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class LudusTransformer(DataTransformer[LudusEvent]):
    pass
