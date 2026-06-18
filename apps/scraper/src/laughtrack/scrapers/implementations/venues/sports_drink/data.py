"""Data model for scraped page data from Sports Drink."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.sports_drink import SportsDrinkEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class SportsDrinkPageData(EventListContainer[SportsDrinkEvent]):
    """Raw extracted event data from the Sports Drink OpenDate page."""

    event_list: List[SportsDrinkEvent]
