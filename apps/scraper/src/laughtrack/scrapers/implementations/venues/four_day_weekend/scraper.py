"""
Four Day Weekend Comedy scraper.

Thin subclass of OvationTixProductionsScraper — specifies client ID (36367),
event class, and discovery URL (club's buy-tickets page). All shared workflow
logic (production discovery → performance API → pricing enrichment) lives in
the base class.
"""

from typing import List

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.four_day_weekend import FourDayWeekendEvent
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.ovationtix_productions_scraper import OvationTixProductionsScraper

from .data import FourDayWeekendPageData
from .transformer import FourDayWeekendEventTransformer

_DEFAULT_CLIENT_ID = "36367"


class FourDayWeekendScraper(OvationTixProductionsScraper):
    """
    Scraper for Four Day Weekend Comedy (Dallas, TX).

    Uses the OvationTix REST API. Production IDs are discovered dynamically from
    the venue's buy-tickets page so that new productions are picked up automatically.
    """

    key = "four_day_weekend"
    default_client_id = _DEFAULT_CLIENT_ID
    event_cls = FourDayWeekendEvent
    page_data_cls = FourDayWeekendPageData
    transformer_cls = FourDayWeekendEventTransformer
    default_name = "Four Day Weekend"

    async def discover_urls(self) -> List[str]:
        return [URLUtils.normalize_url(self.club.scraping_url)]
