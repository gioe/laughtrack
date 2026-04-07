from typing import Any, List, Optional

from asynciolimiter import Limiter

from laughtrack.foundation.models.types import JSONDict
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool
from laughtrack.core.clients.base import BaseApiClient
from laughtrack.core.clients.ovationtix.extractor import extract_next_performance_info


class OvationTixClient(BaseApiClient):
    """Client for interacting with OvationTix's API."""

    def __init__(self, club: Club, proxy_pool: Optional[ProxyPool] = None):
        super().__init__(club, rate_limiter=Limiter(1 / 5, max_burst=1), proxy_pool=proxy_pool)

        # Initialize headers using BaseHeaders
        self.headers = BaseHeaders.get_headers(
            "json",
            Origin="https://ci.ovationtix.com",
            Referer="https://ci.ovationtix.com/",
            clientId="35774",
            newCIRequest="true",
        )

    async def get_ticket_data(self, production_id: str) -> Optional[JSONDict]:
        """
        Get ticket data from OvationTix for a given production ID.

        Returns:
            Optional[JSONDict]: Performance JSON data, or None if failed
        """
        try:
            production_url = f"https://web.ovationtix.com/trs/api/rest/Production({production_id})/performance?"
            production_json = await self.fetch_json(url=production_url, headers=self.headers)
            if not production_json:
                return None

            performance_id, _ = extract_next_performance_info(production_json)
            if not performance_id:
                return None

            performance_url = f"https://web.ovationtix.com/trs/api/rest/Performance({performance_id})"
            performance_json = await self.fetch_json(url=performance_url, headers=self.headers)
            return performance_json
        except Exception:
            return None

    def create_show(self, show_dict: JSONDict) -> Optional[Show]:
        """Create a Show object from the response data."""
        return Show.create(
            **self._extract_basic_show_info(show_dict), timezone=self.club.timezone, club_id=self.club.id
        )

    def _extract_basic_show_info(self, show_dict: JSONDict) -> JSONDict:
        production = show_dict.get("production") or {}
        tickets_available = bool(show_dict.get("ticketsAvailable", True))
        sections = show_dict.get("sections") or []
        url = show_dict.get("url") or ""

        return {
            "name": production.get("productionName"),
            "date": show_dict.get("startDate"),
            "show_page_url": url,
            "description": production.get("description"),
            "tickets": self._extract_ticket_data(sections, url, tickets_available),
        }

    def _extract_ticket_data(
        self, sections: Optional[List[JSONDict]], url: str, tickets_available: bool = True
    ) -> List[Ticket]:
        """Extract ticket information from the JSON-LD dictionary."""
        tickets: List[Ticket] = []

        if sections is None:
            return tickets

        for section in sections:
            tickets_list = section.get("ticketTypeViews") or []
            group_name = section.get("ticketGroupName", "")
            for ticket in tickets_list:
                tickets.append(
                    Ticket(
                        price=ticket.get("price"),
                        purchase_url=url,
                        sold_out=tickets_available is False,
                        type=f"{group_name} - {ticket.get('name')}",
                    )
                )
        return tickets

    async def fetch_events(self, production_id: Optional[str] = None) -> List[Any]:
        """Fetch events from OvationTix. This client works with production IDs."""
        return []
