"""The Setup event transformer."""

from laughtrack.core.entities.event.setup import SetupEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class SetupEventTransformer(DataTransformer[SetupEvent]):
    pass
