"""Page data model for Post Office Cafe & Cabaret scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.post_office_cafe import PostOfficeCafePerformance
from laughtrack.ports.scraping import EventListContainer


@dataclass
class PostOfficeCafePageData(EventListContainer[PostOfficeCafePerformance]):
    """Raw extracted data from Post Office Cafe & Cabaret ThunderTix calendar API."""

    event_list: List[PostOfficeCafePerformance]
