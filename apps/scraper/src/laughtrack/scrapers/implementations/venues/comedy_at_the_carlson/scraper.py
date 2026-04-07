"""
Comedy @ The Carlson scraper.

Thin subclass of OvationTixProductionsScraper — specifies client ID (35843),
event class, and discovery URL (OvationTix calendar page). All shared workflow
logic (production discovery → performance API → pricing enrichment) lives in
the base class.
"""

from typing import List

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.comedy_at_the_carlson import ComedyAtTheCarlsonEvent
from laughtrack.scrapers.base.ovationtix_productions_scraper import OvationTixProductionsScraper

from .data import ComedyAtTheCarlsonPageData
from .transformer import ComedyAtTheCarlsonEventTransformer

_OVATIONTIX_CAL_BASE = "https://web.ovationtix.com/trs/cal"
_DEFAULT_CLIENT_ID = "35843"


class ComedyAtTheCarlsonScraper(OvationTixProductionsScraper):
    """
    Scraper for Comedy @ The Carlson (Rochester, NY).

    Uses the OvationTix REST API. Production IDs are discovered from the
    OvationTix calendar page so that new productions are picked up automatically.
    """

    key = "comedy_at_the_carlson"
    default_client_id = _DEFAULT_CLIENT_ID
    event_cls = ComedyAtTheCarlsonEvent
    page_data_cls = ComedyAtTheCarlsonPageData
    transformer_cls = ComedyAtTheCarlsonEventTransformer
    default_name = "Comedy Show"

    async def discover_urls(self) -> List[str]:
        return [f"{_OVATIONTIX_CAL_BASE}/{_DEFAULT_CLIENT_ID}"]
