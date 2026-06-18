"""Page data for TPAC James K. Polk Theater comedy events."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.tpac_james_k_polk import TpacJamesKPolkEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class TpacJamesKPolkPageData(EventListContainer[TpacJamesKPolkEvent]):
    """Raw extracted TPAC Polk Theater events."""

    event_list: List[TpacJamesKPolkEvent]
