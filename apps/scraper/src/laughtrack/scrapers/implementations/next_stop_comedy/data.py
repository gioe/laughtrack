from dataclasses import dataclass
from typing import List

from laughtrack.ports.scraping import EventListContainer

from .event import NextStopComedyEvent


@dataclass
class NextStopComedyPageData(EventListContainer):
    event_list: List[NextStopComedyEvent]
