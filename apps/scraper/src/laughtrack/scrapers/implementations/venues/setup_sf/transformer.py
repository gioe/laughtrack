"""The Setup SF event transformer."""

from laughtrack.core.entities.event.setup_sf import SetupSFEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class SetupSFEventTransformer(DataTransformer[SetupSFEvent]):
    pass
