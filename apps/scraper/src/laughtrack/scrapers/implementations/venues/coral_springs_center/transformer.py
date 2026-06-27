"""Coral Springs Center for the Arts event transformer."""

from laughtrack.core.entities.event.coral_springs_center import (
    CoralSpringsCenterEvent,
)
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class CoralSpringsCenterEventTransformer(DataTransformer[CoralSpringsCenterEvent]):
    pass
