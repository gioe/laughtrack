"""
Tessera API client for fetching ticket information.

This client handles interactions with Tessera-based ticketing systems,
including proper authentication headers and data parsing.
Refactored to inherit from BaseApiClient to unify HTTP and logging behavior.
"""

from typing import Any, Dict, List, Optional

from curl_cffi.requests import AsyncSession

from laughtrack.core.clients.tessera.models.response import TesseraAPIResponse
from laughtrack.core.clients.base import BaseApiClient
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.ticket.local.broadway import BroadwayTicket
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool
from laughtrack.foundation.utilities.url import URLUtils


class TesseraClient(BaseApiClient):
    """
    Client for interacting with Tessera ticketing API.

    This class handles:
    - API authentication and headers
    - Ticket data fetching
    - Response parsing
    - Error handling
    """

    def __init__(
        self,
        club: Club,
        base_domain: str,
        api_base_url: str,
        origin_url: str,
        proxy_pool: Optional[ProxyPool] = None,
    ):
        """
        Initialize the Tessera client.

        Args:
            base_domain: The base domain for the venue (e.g., "broadwaycomedyclub.com")
            api_base_url: The base URL for the Tessera API
            origin_url: The origin URL for CORS headers
        """
        # Store origin_url before calling super so _initialize_headers can use it
        self.origin_url = origin_url
        super().__init__(club, proxy_pool=proxy_pool)

        self.base_domain = base_domain
        self.api_base_url = api_base_url
        # Root API URL (strips the resource-specific path suffix, e.g. "/products")
        # Used for auth endpoints like /authorization/session.
        self.api_root_url = api_base_url.rstrip("/").rsplit("/", 1)[0]
    # No per-client concurrency management; batching lives in scrapers

    async def refresh_session_id(self) -> bool:
        """Fetch a fresh session ID from the Tessera authorization endpoint.

        The Tessera API returns HTTP 200 + empty body when the session ID is
        expired.  Call this once per scrape run to avoid silent failures.

        Returns:
            True if a new session ID was acquired and applied, False otherwise.
        """
        auth_url = f"{self.api_root_url}/authorization/session"
        try:
            async with AsyncSession(
                impersonate=self._get_impersonation_target(auth_url)
            ) as session:
                response = await session.post(
                    auth_url,
                    headers={
                        "Content-Type": "application/json",
                        "Origin": self.origin_url,
                    },
                )
            if response.status_code != 200 or not response.text.strip():
                self.log_warning(
                    f"Tessera session refresh failed: HTTP {response.status_code}"
                    f" | url={auth_url}"
                )
                return False
            data = response.json()
            session_id = data.get("sessionId") if isinstance(data, dict) else None
            if not session_id:
                self.log_warning(f"Tessera session refresh returned no sessionId | url={auth_url}")
                return False
            self.headers["sessionid"] = session_id
            self.log_info(f"Tessera session refreshed successfully")
            return True
        except Exception as e:
            self.log_warning(f"Tessera session refresh error: {e} | url={auth_url}")
            return False

    def _initialize_headers(self) -> Dict[str, str]:
        """Initialize default headers for Tessera API using BaseHeaders."""
        headers = BaseHeaders.get_headers(
            base_type="json", domain=self.origin_url, referer=f"{self.origin_url}/shows/"
        )
        # Add Tessera-specific sessionid
        headers["sessionid"] = (
            "RUFBQUFOVWdyOEtjcm55TU5wZlZnRnRnVmdrVEwzRDhWNldOMjlReExJcDZ6MzZHWUhTN25zQjJNTllqK1RpeEpoYVBQQnNGdlZpeC96bWhpNzRCdHpVME1Wcz0="
        )
        return headers

    async def _fetch_ticket_data(self, event_id: str) -> Optional[TesseraAPIResponse]:
        """
        Fetch raw ticket data from Tessera API.

        The Tessera API returns HTTP 200 with an empty body for expired/stale
        events.  Using a raw session here (rather than fetch_json) lets us
        detect that case and log at WARNING rather than ERROR.

        Args:
            event_id: Event ID for API call

        Returns:
            TesseraAPIResponse dictionary or None if failed
        """
        api_url = f"{self.api_base_url}/{event_id}"
        normalized_url = URLUtils.normalize_url(api_url)

        try:
            await self._apply_rate_limit(normalized_url)
            async with AsyncSession(
                impersonate=self._get_impersonation_target(normalized_url)
            ) as session:
                response = await session.get(normalized_url, headers=self.headers)

            body = response.text.strip() if response.text else ""
            if not body:
                self.log_warning(
                    f"Empty response for event {event_id} — event may be stale or expired"
                    f" | url={normalized_url}"
                )
                return None

            parsed_response = response.json()
            if not parsed_response or not isinstance(parsed_response, dict):
                self.log_warning(
                    f"Invalid response for event {event_id}: expected dict,"
                    f" got {type(parsed_response)} | url={normalized_url}"
                )
                return None

            return TesseraAPIResponse.from_dict(parsed_response)

        except Exception as e:
            self.log_error(f"Error fetching ticket data for event {event_id}: {str(e)}")
            return None

    async def get_ticket(self, event_id: str) -> List[BroadwayTicket]:
        """
        Get parsed BroadwayTicket objects for an event with full Tessera data.

        Args:
            event_id: Event ID for API call

        Returns:
            List of ticket-like objects with rich Tessera-specific data
        """
        ticket_data = await self._fetch_ticket_data(event_id)
        if not ticket_data:
            self.log_warning(f"Failed to fetch ticket data for event {event_id}")
            return []

        # Parse the ticket data into ticket objects
        return self.parse_ticket_data(ticket_data, event_id)

    def parse_ticket_data(self, ticket_data: TesseraAPIResponse, event_id: str) -> List[BroadwayTicket]:
        """
        Parse ticket data from Tessera API response.

        Args:
            ticket_data: TesseraAPIResponse from Tessera API
            event_id: Event ID for ticket URL

        Returns:
            List of ticket-like objects
        """
        # Extract campaigns (ticket types) from the response using attribute access
        campaigns = ticket_data.campaigns or []

        # Create BroadwayTicket adapter objects directly from each campaign
        tickets: List[BroadwayTicket] = []
        for campaign in campaigns:
            try:
                adapter = BroadwayTicket.from_tessera_campaign(
                    campaign,
                    event_id=event_id,
                    base_domain=self.base_domain,
                    fallback_seating_chart_url=ticket_data.seatingChartUrl,
                )
                tickets.append(adapter)
            except Exception as e:
                # If anything goes wrong, skip the campaign and continue
                self.log_warning(f"Failed to adapt Tessera campaign to BroadwayTicket: {e}")

        if not tickets:
            self.log_warning(f"Failed to parse ticket data for event {event_id}")

        return tickets
