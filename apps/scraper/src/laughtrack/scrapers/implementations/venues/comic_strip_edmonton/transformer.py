"""The Comic Strip Edmonton event transformer."""

from laughtrack.core.entities.event.comic_strip_edmonton import ComicStripEdmontonEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class ComicStripEdmontonTransformer(DataTransformer[ComicStripEdmontonEvent]):
    pass
