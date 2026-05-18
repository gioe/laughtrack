"""
Tixologi-backed venue client.

Laugh Factory Reno uses Tixologi (tixologi.com) as its ticketing platform
(partner ID 690).  The Tixologi API does NOT expose a public events endpoint —
`api-v2.tixologi.com/public/users/partners/690/events` returns 401 Unauthorized.

Instead, shows are server-rendered as `.show-sec.jokes` HTML divs on the venue's
own CMS page (www.laughfactory.com/reno).  This client fetches that HTML page so
the venue-level extractor can parse it.

Tixologi ticket links follow the pattern:
  https://www.laughfactory.club/checkout/show/{punchup_id}
where `punchup_id` is a UUID embedded in the `href` attribute of
`.reno-ticket-button[data-punchupid]` or `a.readmore-btn.ticket-toggle-btn`.

API reference (no auth required):
  GET https://api-v2.tixologi.com/public/users/partners/690
  → returns partner metadata: name "Laugh Factory - Long Beach", punchup_id UUID
"""

from typing import Any, Dict, List, Optional

from laughtrack.core.clients.base import BaseApiClient
from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger


class TixologiClient(BaseApiClient):
    """
    HTTP client for Tixologi-backed venue pages.

    Fetches the Laugh Factory CMS HTML page that contains server-rendered show
    listings.  The actual event parsing is delegated to the venue-level extractor.
    """

    # Tixologi partner ID for Laugh Factory Reno
    PARTNER_ID = 690
    EVENT_API_BASE_URL = "https://api-v2.tixologi.com/public/ticketing/events"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)

    async def fetch_shows_page(self, url: str) -> Optional[str]:
        """
        Fetch the HTML page that contains show listings for the venue.

        Args:
            url: The CMS page URL (e.g. https://www.laughfactory.com/reno)

        Returns:
            HTML content as a string, or None if the fetch fails.
        """
        html = await self.fetch_html(url)
        if not html:
            Logger.info(
                f"TixologiClient: no HTML returned from {url}",
                {"club": self.club.name},
            )
        return html

    @classmethod
    def event_api_endpoint(cls, event_id: str | int) -> str:
        """Return Tixologi's public ticketing event endpoint."""
        return f"{cls.EVENT_API_BASE_URL}/{event_id}?active=true"

    async def fetch_event_ticket_types(self, event_id: str | int) -> List[Dict[str, Any]]:
        """Fetch public ticket type data for a Tixologi event."""
        event_id_str = str(event_id).strip()
        if not event_id_str:
            return []

        payload = await self.fetch_json(
            self.event_api_endpoint(event_id_str),
            logger_context={"club": self.club.name, "tixologi_event_id": event_id_str},
        )
        if not isinstance(payload, dict):
            return []

        ticket_types = payload.get("ticket_types")
        if not isinstance(ticket_types, list):
            return []

        return [
            ticket_type
            for ticket_type in ticket_types
            if isinstance(ticket_type, dict)
        ]
