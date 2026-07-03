"""FullCalendar JSON event transformer."""

from laughtrack.core.entities.event.fullcalendar_json import FullCalendarJsonEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class FullCalendarJsonEventTransformer(DataTransformer[FullCalendarJsonEvent]):
    pass
