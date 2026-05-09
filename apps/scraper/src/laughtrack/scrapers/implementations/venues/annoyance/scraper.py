"""
The Annoyance Theatre Chicago scraper.

The Annoyance Theatre (851 W. Belmont Ave, Chicago, IL) uses ThunderTix for
ticketing.  Upcoming shows are available via the ThunderTix calendar API:

  GET https://theannoyance.thundertix.com/reports/calendar?week=0&start={ts}&end={ts+7d}

The API returns a JSON array of performance objects, one per show.  A single
request covers one 7-day window; to collect 12 weeks of upcoming shows the
scraper generates 12 weekly URLs starting from the current Sunday.

Filtering rules:
- Skip events whose title starts with "CLASS:" or "TRAINING CENTER:".
- Skip events where publicly_available is False.

Pipeline:
  1. collect_scraping_targets() → 12 weekly ThunderTix API URLs
  2. get_data(url)              → fetch JSON, filter, return AnnoyancePageData
  3. transformation_pipeline    → AnnoyancePerformance.to_show() → Show objects
"""

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.annoyance import AnnoyancePerformance
from laughtrack.scrapers.implementations.api.thundertix.scraper import (
    ThunderTixCalendarConfig,
    ThunderTixCalendarScraper,
)

from .data import AnnoyancePageData
from .transformer import AnnoyanceEventTransformer

_BASE_URL = "https://theannoyance.thundertix.com"
_TITLE_SKIP_PREFIXES = ("CLASS:", "TRAINING CENTER:")


class AnnoyanceTheatreScraper(ThunderTixCalendarScraper[AnnoyancePerformance, AnnoyancePageData]):
    """Scraper for The Annoyance Theatre Chicago via ThunderTix calendar API."""

    key = "annoyance"
    thundertix_config = ThunderTixCalendarConfig(
        base_url=_BASE_URL,
        event_factory=AnnoyancePerformance.from_api_response,
        page_data_factory=lambda events: AnnoyancePageData(event_list=events),
        title_skip_prefixes=_TITLE_SKIP_PREFIXES,
    )

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(AnnoyanceEventTransformer(club))
