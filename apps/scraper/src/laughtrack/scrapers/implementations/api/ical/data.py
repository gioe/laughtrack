"""Page data container for the generic ical (iCalendar / Google Calendar) scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.ical_event import IcalEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class IcalPageData(EventListContainer[IcalEvent]):
    """Raw extracted event data from an ICS feed."""

    event_list: List[IcalEvent]
