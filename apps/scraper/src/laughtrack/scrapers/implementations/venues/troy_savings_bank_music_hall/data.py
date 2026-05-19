"""Page data for Troy Savings Bank Music Hall event pages."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.troy_savings_bank_music_hall import (
    TroySavingsBankMusicHallEvent,
)


@dataclass
class TroySavingsBankMusicHallPageData:
    """Raw extracted events from one Troy Savings Bank Music Hall page."""

    event_list: List[TroySavingsBankMusicHallEvent]
