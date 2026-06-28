"""WellAttended event transformer."""

from laughtrack.core.entities.event.wellattended import WellAttendedEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class WellAttendedEventTransformer(DataTransformer[WellAttendedEvent]):
    """Transforms WellAttendedEvent objects into Show objects via event.to_show()."""

    pass
