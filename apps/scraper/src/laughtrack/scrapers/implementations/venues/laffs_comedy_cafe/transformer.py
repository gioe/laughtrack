"""Laffs Comedy Cafe event transformer."""

from laughtrack.core.entities.event.laffs_comedy_cafe import LaffsComedyCafeEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class LaffsComedyCafeEventTransformer(DataTransformer[LaffsComedyCafeEvent]):
    pass
