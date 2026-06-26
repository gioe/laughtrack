"""ical event transformer for the generic iCalendar scraper."""

from laughtrack.core.entities.event.ical_event import IcalEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class IcalEventTransformer(DataTransformer[IcalEvent]):
    """Transforms IcalEvent objects into Show objects via event.to_show()."""

    pass
