"""Data container for Wix/Velo _functions/shows events."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.wix_functions_shows import WixFunctionsShowEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class WixFunctionsShowsPageData(EventListContainer[WixFunctionsShowEvent]):
    """Raw extracted event data from a custom Wix/Velo shows endpoint."""

    event_list: List[WixFunctionsShowEvent]
