"""Page data for House of Comedy British Columbia."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.house_of_comedy_bc import HouseOfComedyBcEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class HouseOfComedyBcPageData(EventListContainer[HouseOfComedyBcEvent]):
    """Webflow event cards extracted from the BC homepage."""

    event_list: List[HouseOfComedyBcEvent]
