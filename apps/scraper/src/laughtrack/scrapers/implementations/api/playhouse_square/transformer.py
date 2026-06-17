"""Playhouse Square event transformer.

PlayhouseSquareEvent implements ShowConvertible.to_show(), so the transformer is
a thin DataTransformer subtype — the pipeline calls to_show() on each event.
"""

from laughtrack.core.entities.event.playhouse_square import PlayhouseSquareEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class PlayhouseSquareEventTransformer(DataTransformer[PlayhouseSquareEvent]):
    pass
