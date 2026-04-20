"""
Tessera API client for fetching ticket information.

This client handles interactions with Tessera-based ticketing systems,
including proper authentication headers and data parsing.

Routes both the auth POST (``refresh_session_id``) and the ticket GET
(``_fetch_ticket_data``) through the BaseApiClient / HttpClient helpers so
Cloudflare-style 403s and empty-body challenge responses hit the shared
Playwright fallback (A2) and bot-block detection (A3) added in TASK-1648.
"""

from typing import Dict, List, Optional

from laughtrack.core.clients.tessera.models.response import TesseraAPIResponse
from laughtrack.core.clients.base import BaseApiClient
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.ticket.local.broadway import BroadwayTicket
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool


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

        Delegates to ``BaseApiClient.post_json`` so bot-block (Cloudflare /
        DataDome) responses surface as ERROR logs and non-200 / empty-body
        failures are no longer swallowed silently (A3, TASK-1651).

        Returns:
            True if a new session ID was acquired and applied, False otherwise.
        """
        auth_url = f"{self.api_root_url}/authorization/session"
        # payload=None → curl-cffi sends no JSON body, matching the prior
        # direct-post shape.  post_json auto-adds Content-Type: application/json.
        data = await self.post_json(
            auth_url,
            payload=None,
            headers={"Origin": self.origin_url},
            logger_context={"action": "refresh_session_id"},
        )
        if data is None:
            # post_json already logged the specific failure (bot-block / non-200 /
            # empty body) at ERROR level.
            return False
        session_id = data.get("sessionId")
        if not session_id:
            self.log_warning(f"Tessera session refresh returned no sessionId | url={auth_url}")
            return False
        self.headers["sessionid"] = session_id
        self.log_info("Tessera session refreshed successfully")
        return True

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

        Delegates to ``BaseApiClient.fetch_json`` → ``HttpClient.fetch_json`` so
        a Cloudflare/DataDome 403 or an HTTP-200 challenge body is retried via
        the Playwright headless browser (A2, TASK-1650).  Tessera's known
        "stale event" signal (HTTP 200 + empty body) now triggers the fallback
        as well — the browser replay returns empty too, so the final result
        is still ``None`` and the scraper path is unchanged, but we gain
        genuine challenge recovery for the 403 case at the cost of one
        fallback attempt per stale event.

        Args:
            event_id: Event ID for API call

        Returns:
            TesseraAPIResponse dictionary or None if failed.
        """
        api_url = f"{self.api_base_url}/{event_id}"
        parsed_response = await self.fetch_json(
            api_url,
            headers=self.headers,
            logger_context={"event_id": event_id},
        )
        if parsed_response is None:
            # fetch_json already logged the specific failure (non-200 / empty
            # body / unparseable after fallback).  For Tessera this commonly
            # means a stale event — retain a client-side warn for that signal.
            self.log_warning(
                f"No ticket data for event {event_id} — event may be stale, expired, or blocked"
            )
            return None
        if not isinstance(parsed_response, dict):
            self.log_warning(
                f"Invalid response for event {event_id}: expected dict,"
                f" got {type(parsed_response).__name__}"
            )
            return None
        return TesseraAPIResponse.from_dict(parsed_response)

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
