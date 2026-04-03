"""
Data model for CSz Philadelphia (ComedySportz) scraper.

VBO Tickets is the ticketing platform used by CSz Philadelphia.
Each CszPhillyShowInstance represents a single scheduled performance
extracted from the VBO date-selector widget.
"""

from dataclasses import dataclass
from typing import List

from laughtrack.ports.scraping import EventListContainer


@dataclass
class CszPhillyShowInstance:
    """
    A single scheduled show instance from the VBO Tickets date slider.

    Attributes:
        event_id: VBO event ID (eid parameter)
        event_date_id: VBO event-date ID (edid parameter) for this specific instance
        event_name: Show title (e.g. "ComedySportz", "TV Power Hour")
        month: 3-letter month abbreviation (e.g. "Mar", "Apr")
        day: Day of the month (1–31)
        weekday: Day-of-week abbreviation (e.g. "Sat", "Fri")
        time: Show time string (e.g. "7:00 PM")
    """

    event_id: int
    event_date_id: int
    event_name: str
    month: str
    day: int
    weekday: str
    time: str


@dataclass
class CszPhillyPageData(EventListContainer[CszPhillyShowInstance]):
    """Raw extracted data from the CSz Philadelphia VBO Tickets plugin."""

    event_list: List[CszPhillyShowInstance]
