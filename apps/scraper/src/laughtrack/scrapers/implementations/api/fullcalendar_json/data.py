"""Data container for FullCalendar JSON feed events."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.fullcalendar_json import FullCalendarJsonEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class FullCalendarJsonPageData(EventListContainer[FullCalendarJsonEvent]):
    """Raw extracted event data from a FullCalendar JSON feed."""

    event_list: List[FullCalendarJsonEvent]
