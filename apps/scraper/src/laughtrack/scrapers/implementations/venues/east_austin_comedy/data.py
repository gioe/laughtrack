"""Data model for scraped page data from East Austin Comedy."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.east_austin_comedy import EastAustinComedyEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class EastAustinComedyPageData(EventListContainer[EastAustinComedyEvent]):
    """
    Container for EastAustinComedyEvent objects extracted from the Netlify
    availability API, following the standard PageData pattern.
    """

    event_list: List[EastAustinComedyEvent]
