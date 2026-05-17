"""Page data for TPAC James K. Polk Theater comedy events."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.tpac_james_k_polk import TpacJamesKPolkEvent


@dataclass
class TpacJamesKPolkPageData:
    """Raw extracted TPAC Polk Theater events."""

    event_list: List[TpacJamesKPolkEvent]
