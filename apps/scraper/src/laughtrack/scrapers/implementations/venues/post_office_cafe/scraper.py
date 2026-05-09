"""
Post Office Cafe & Cabaret (Provincetown, MA) scraper.

Post Office Cafe & Cabaret (303 Commercial St, Provincetown, MA) uses ThunderTix
for ticketing.  Upcoming shows are available via the ThunderTix calendar API:

  GET https://postofficecafecabaret.thundertix.com/reports/calendar?week=0&start={ts}&end={ts+7d}

The API returns a JSON array of performance objects, one per show.  A single
request covers one 7-day window; to collect 12 weeks of upcoming shows the
scraper generates 12 weekly URLs starting from the current Sunday.

Filtering rules:
- Skip events where publicly_available is False.

Pipeline:
  1. collect_scraping_targets() → 12 weekly ThunderTix API URLs
  2. get_data(url)              → fetch JSON, filter, return PostOfficeCafePageData
  3. transformation_pipeline    → PostOfficeCafePerformance.to_show() → Show objects
"""

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.post_office_cafe import PostOfficeCafePerformance
from laughtrack.scrapers.implementations.api.thundertix.scraper import (
    ThunderTixCalendarConfig,
    ThunderTixCalendarScraper,
)

from .data import PostOfficeCafePageData
from .transformer import PostOfficeCafeEventTransformer

_BASE_URL = "https://postofficecafecabaret.thundertix.com"


class PostOfficeCafeScraper(ThunderTixCalendarScraper[PostOfficeCafePerformance, PostOfficeCafePageData]):
    """Scraper for Post Office Cafe & Cabaret via ThunderTix calendar API."""

    key = "post_office_cafe"
    thundertix_config = ThunderTixCalendarConfig(
        base_url=_BASE_URL,
        event_factory=PostOfficeCafePerformance.from_api_response,
        page_data_factory=lambda events: PostOfficeCafePageData(event_list=events),
    )

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(PostOfficeCafeEventTransformer(club))
