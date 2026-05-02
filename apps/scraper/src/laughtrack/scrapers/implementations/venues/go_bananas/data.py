"""Page data for Go Bananas Comedy Club."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.go_bananas import GoBananasEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class GoBananasPageData(EventListContainer[GoBananasEvent]):
    event_list: List[GoBananasEvent]
