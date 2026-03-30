"""
Ninkashi API client for fetching upcoming events.

Ninkashi is a ticketing platform used by venues like Cheaper Than Therapy
(tickets.cttcomedy.com). The public API requires no authentication.

API endpoint:
  GET https://api.ninkashi.com/public_access/events/find_by_url_site
      ?url_site=<subdomain>&page=<n>&per_page=<n>

Response: a root-level JSON array of event objects.
"""

from typing import List, Optional
from urllib.parse import urlencode

from laughtrack.core.clients.base import BaseApiClient
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.ninkashi import NinkashiEvent
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool
from laughtrack.foundation.infrastructure.logger.logger import Logger


class NinkashiClient(BaseApiClient):
    """Client for the Ninkashi public events API."""

    BASE_URL = "https://api.ninkashi.com/public_access/events/find_by_url_site"
    PER_PAGE = 100

    def __init__(self, club: Club, proxy_pool: Optional[ProxyPool] = None):
        super().__init__(club, proxy_pool=proxy_pool)
        self.logger_context = club.as_context()

    async def fetch_events(self, url_site: str) -> List[NinkashiEvent]:
        """
        Fetch all upcoming events for the given url_site, paginating as needed.

        Returns an empty list on network failure or unexpected response format.
        """
        events: List[NinkashiEvent] = []
        page = 1
        while True:
            qs = urlencode({"url_site": url_site, "page": page, "per_page": self.PER_PAGE})
            url = f"{self.BASE_URL}?{qs}"
            response = await self.fetch_json_list(url)
            if response is None:
                Logger.warn(
                    f"NinkashiClient: no list response on page {page} for {url_site} — stopping pagination",
                    self.logger_context,
                )
                break

            if not response:
                break

            for raw in response:
                if not isinstance(raw, dict):
                    continue
                try:
                    events.append(NinkashiEvent.from_dict(raw, url_site))
                except Exception as e:
                    Logger.warn(
                        f"NinkashiClient: skipping malformed event — {e}",
                        self.logger_context,
                    )

            if len(response) < self.PER_PAGE:
                break
            page += 1

        return events
