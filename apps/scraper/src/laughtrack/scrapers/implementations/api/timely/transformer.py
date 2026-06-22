"""Timely event transformer."""

from laughtrack.core.entities.event.timely import TimelyEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class TimelyTransformer(DataTransformer[TimelyEvent]):
    """Transforms TimelyEvent objects via TimelyEvent.to_show."""

    pass

