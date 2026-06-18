"""Data container for Tessitura TNEW scraped events."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.tessitura_tnew import TessituraTNEWEvent


@dataclass
class TessituraTNEWPageData:
    """Container for performances extracted from a TNEW production-season API."""

    event_list: List[TessituraTNEWEvent]
