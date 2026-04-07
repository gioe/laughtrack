"""
Generic OvationTix platform scraper.

Serves all venues that use OvationTix for ticketing. Per-venue configuration
(client ID, discovery URL) is read from the Club model — no per-venue
subclassing needed.

Venues served:
- Comedy @ The Carlson (client_id=35843)
- Four Day Weekend Comedy (client_id=36367)
- Uncle Vinnie's Comedy Club (client_id=35774)
"""

from typing import List

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.ovationtix import OvationTixEvent
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.ovationtix_productions_scraper import OvationTixProductionsScraper

from .data import OvationTixPageData
from .transformer import OvationTixEventTransformer


class OvationTixScraper(OvationTixProductionsScraper):
    """
    Generic scraper for all OvationTix-backed venues.

    Reads the club's ovationtix_client_id and scraping_url from the DB.
    The scraping_url should point to either the OvationTix calendar page
    (web.ovationtix.com/trs/cal/{client_id}) or the venue's buy-tickets page
    containing OvationTix widgets.
    """

    key = "ovationtix"
    event_cls = OvationTixEvent
    page_data_cls = OvationTixPageData
    transformer_cls = OvationTixEventTransformer
    default_name = "Comedy Show"
    default_client_id = ""  # Set per-instance from club config

    def __init__(self, club: Club, **kwargs):
        if not club.ovationtix_client_id:
            raise ValueError(f"Club {club.name} does not have an ovationtix_client_id configured")
        # Instance attribute shadows ClassVar so the base class reads the right value
        self.default_client_id = club.ovationtix_client_id
        super().__init__(club, **kwargs)

    async def discover_urls(self) -> List[str]:
        """Return the club's scraping_url as the discovery page."""
        return [URLUtils.normalize_url(self.club.scraping_url)]
