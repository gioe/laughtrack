"""Page data for Rick Bronson's House of Comedy Phoenix."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.house_of_comedy_phoenix import (
    HouseOfComedyPhoenixEvent,
)


@dataclass
class HouseOfComedyPhoenixPageData:
    """Container for Phoenix show rows parsed from the WordPress AJAX response."""

    event_list: List[HouseOfComedyPhoenixEvent]
