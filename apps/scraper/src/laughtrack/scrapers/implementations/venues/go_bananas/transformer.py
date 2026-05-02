"""Go Bananas event transformer."""

from laughtrack.core.entities.event.go_bananas import GoBananasEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class GoBananasEventTransformer(DataTransformer[GoBananasEvent]):
    pass
