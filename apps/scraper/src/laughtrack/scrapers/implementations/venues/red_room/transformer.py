"""RED ROOM Comedy Club event transformer."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from .extractor import RedRoomEvent


class RedRoomEventTransformer(DataTransformer[RedRoomEvent]):
    pass
