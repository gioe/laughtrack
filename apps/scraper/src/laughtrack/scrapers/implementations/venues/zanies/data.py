"""Data model for scraped page data from Zanies Comedy Club."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.zanies import ZaniesEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class ZaniesPageData(EventListContainer[ZaniesEvent]):
    """Raw extracted event data from a Zanies Comedy Club page."""

    event_list: List[ZaniesEvent]
