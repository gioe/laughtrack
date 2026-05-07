"""Page data for The Comic Strip West Edmonton Mall."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.comic_strip_edmonton import ComicStripEdmontonEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class ComicStripEdmontonPageData(EventListContainer[ComicStripEdmontonEvent]):
    """Webflow event cards extracted from the official Edmonton homepage."""

    event_list: List[ComicStripEdmontonEvent]
