"""UCB event transformer."""

from laughtrack.core.entities.event.ucb import UCBEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class UCBEventTransformer(DataTransformer[UCBEvent]):
    pass
