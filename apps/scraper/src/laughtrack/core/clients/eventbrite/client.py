from typing import List, Optional
from urllib.parse import urlencode

from laughtrack.utilities.infrastructure import RateLimiter

from laughtrack.core.entities.event.eventbrite import EventbriteEvent
from laughtrack.core.entities.club.model import Club
from laughtrack.infrastructure.config.config_manager import ConfigManager
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool
from laughtrack.core.clients.base import BaseApiClient
from laughtrack.foundation.infrastructure.logger.logger import Logger
from .models import EventbriteListEventsResponse, EventbriteSingleEventResponse

class EventbriteClient(BaseApiClient):
    """Client for interacting with Eventbrite's API."""

    # API Constants
    BASE_URL = "https://www.eventbriteapi.com/v3"
    REQUEST_TIMEOUT = 30
    RATE_LIMIT = 5.0  # requests per second

    # Browser headers for web scraping fallback
    BROWSER_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
    }

    def __init__(self, club: Club, proxy_pool: Optional[ProxyPool] = None):
        """Initialize the Eventbrite client for a specific club/venue.

        Contract
        - Input: a ``Club`` domain object where ``club.eventbrite_id`` may be set.
        - Output: instantiated client with headers and rate limiter configured.
        - Side effects: config lookup for API token, global rate limit set for
          "eventbrite.com" via shared ``RateLimiter`` instance, debug logs.

        Notes for verification
        - Ensure a bearer token exists in config path (api.eventbrite_token).
        - Verify domain-specific RPS limit equals ``RATE_LIMIT`` (5.0 by default).
        - For clubs without ``eventbrite_id``, the client still initializes but
          list calls will short‑circuit and return an empty list.
        """
        # Initialize with shared project rate limiter; set/ensure domain limit
        limiter = RateLimiter()
        limiter.set_domain_limit("eventbrite.com", self.RATE_LIMIT)
        super().__init__(club, limiter, proxy_pool=proxy_pool)

        # DEBUG: client initialization details
        try:
            Logger.debug(
                "EventbriteClient initialized",
                context={
                    "club_name": getattr(club, "name", "-"),
                    "eventbrite_venue_id": getattr(club, "eventbrite_id", None),
                    "rate_limit_rps": self.RATE_LIMIT,
                },
            )
        except Exception:
            pass

        # Static params for list calls
        self.params = {
            "status": "live",
            "order_by": "start_asc",
            "only_public": "true",
            "expand": "ticket_availability",
        }

    def _initialize_headers(self) -> dict:
        """Build default JSON API headers with Eventbrite bearer token.

        Returns
        - dict: Headers including Authorization, Content-Type, and Accept for
          JSON requests, suitable for Eventbrite API endpoints.

        Verification
        - Token source: ``ConfigManager.get_config('api', 'eventbrite_token')``.
        - ``Authorization`` must be ``Bearer <token>``.
        - Intended for use by BaseApiClient.fetch_json; not used for browser
          fallback scraping (see ``BROWSER_HEADERS``).
        """
        token = ConfigManager.get_config("api", "eventbrite_token")
        return BaseHeaders.get_headers("json", auth_type="eventbrite", auth_token=token)

    async def fetch_all_events(self) -> List[EventbriteEvent]:
        """Fetch all live events for the configured venue, handling pagination.

        Behavior
        - If ``self.club.eventbrite_id`` is falsy, returns ``[]`` immediately.
        - Iteratively calls :meth:`fetch_eventbrite_event_list` following
          continuation tokens until no further pages are available.
        - Converts API models to domain ``EventbriteEvent`` instances via
          ``EventbriteEvent.from_api_model``.

        Returns
        - list[EventbriteEvent]: Flattened list across all pages; ``[]`` on
          no id, no data, or error paths where pages produce no events.

        Verification checklist
        - Pagination proceeds while ``pagination.has_more_items`` is true.
        - Accumulated event count equals the sum of page event counts.
        - Logging emits debug entries for start, each page, and completion.

        Edge cases
        - Network/API failures cause a page to return ``None`` which stops the
          loop; function returns whatever was collected so far (possibly ``[]``).
        - If a page contains ``events=[]`` but indicates more pages, current
          logic will break; validate upstream API expectations in tests.
        """
        events = []
        continuation = None

        if not self.club.eventbrite_id:
            return []

        try:
            Logger.debug(
                "Fetching all Eventbrite events (paginated)",
                context={
                    "club_name": getattr(self.club, "name", "-"),
                    "venue_id": getattr(self.club, "eventbrite_id", None),
                },
            )
        except Exception:
            pass

        while True:
            # Fetch a page of events
            response = await self.fetch_eventbrite_event_list(
                venue_id=self.club.eventbrite_id,
                continuation=continuation,
            )

            if not response or not response.events:
                break

            # Convert API events to domain events
            domain_events = [EventbriteEvent.from_api_model(api_event) for api_event in response.events]
            events.extend(domain_events)

            # Check if more pages exist
            try:
                Logger.debug(
                    "Fetched Eventbrite page",
                    context={
                        "club_name": getattr(self.club, "name", "-"),
                        "venue_id": getattr(self.club, "eventbrite_id", None),
                        "page_events": len(response.events) if response else 0,
                        "has_more": bool(response and response.pagination and response.pagination.has_more_items),
                    },
                )
            except Exception:
                pass

            if not response.pagination.has_more_items:
                break
            continuation = response.pagination.continuation

        try:
            Logger.debug(
                "Completed Eventbrite pagination",
                context={
                    "club_name": getattr(self.club, "name", "-"),
                    "venue_id": getattr(self.club, "eventbrite_id", None),
                    "total_events": len(events),
                },
            )
        except Exception:
            pass

        return events

    async def fetch_eventbrite_event_list(
        self, venue_id: str, continuation: Optional[str] = None
    ) -> Optional[EventbriteListEventsResponse]:
        """Fetch a single page of events for a venue.

        Args:
        - venue_id: The Eventbrite venue ID to fetch events for.
        - continuation: Pagination token for next page (as returned by the API).

        Returns:
        - EventbriteListEventsResponse with events and pagination info, or ``None``
          when the HTTP request fails or returns no data.

        Verification checklist
        - Request URL format: ``{BASE_URL}/venues/{venue_id}/events/?<query>`` where
          query includes status=live, order_by=start_asc, only_public=true,
          expand=ticket_availability, and optional continuation.
        - Response parsing uses ``EventbriteListEventsResponse.from_dict``.
        - ``resp.pagination.continuation`` is used by callers for next page.

        Edge cases
        - If API returns unexpected schema, ``from_dict`` may raise; upstream
          caller relies on ``fetch_json`` returning ``None`` on errors to avoid
          raising here. Consider adding stricter guards if needed.
        """
        fetch_events_url = f"{self.BASE_URL}/venues/{venue_id}/events/"

        # Fetch single page only
        req_params = self.params.copy()
        if continuation:
            req_params["continuation"] = continuation
        query_string = urlencode(req_params)
        full_url = f"{fetch_events_url}?{query_string}"
        try:
            Logger.debug(
                "Requesting Eventbrite event list",
                context={
                    "club_name": getattr(self.club, "name", "-"),
                    "venue_id": venue_id,
                    "url": full_url,
                    "has_continuation": bool(continuation),
                },
            )
        except Exception:
            pass

        # Use base client's convenience method
        # For Eventbrite list endpoints, remove Content-Type so query params aren't ignored
        req_headers = dict(self.headers)
        req_headers.pop("Content-Type", None)

        data = await self.fetch_json(
            url=full_url,
            headers=req_headers,
            timeout=self.REQUEST_TIMEOUT,
            logger_context={"venue_id": venue_id},
        )

        if not data:
            return None

        # Return single page response
        resp = EventbriteListEventsResponse.from_dict(data)
        try:
            Logger.debug(
                "Parsed Eventbrite event list page",
                context={
                    "club_name": getattr(self.club, "name", "-"),
                    "venue_id": venue_id,
                    "events": len(resp.events) if resp and resp.events else 0,
                    "has_more": bool(resp and resp.pagination and resp.pagination.has_more_items),
                },
            )
        except Exception:
            pass
        return resp

    async def retrieve_event(self, event_id: str) -> Optional[EventbriteSingleEventResponse]:
        """Retrieve details for a single Eventbrite event by id.

        Args
        - event_id: Eventbrite event identifier (string).

        Returns
        - EventbriteSingleEventResponse on success, otherwise ``None`` when the
          event is not found or the request fails. A warning is logged on miss.

        Verification checklist
        - Endpoint: ``{BASE_URL}/events/{event_id}/`` with JSON headers and bearer token.
        - Parsing uses ``EventbriteSingleEventResponse.from_json_dict``.
        - On missing/empty data, method logs a warning and returns ``None``.

        Edge cases
        - Non-200 responses should cause ``fetch_json`` to return ``None``.
        - Partial payloads should map safely via ``from_json_dict``; add tests for
          absent optional fields like ``name`` or ``status``.
        """
        try:
            retrieve_event_url = f"{self.BASE_URL}/events/{event_id}/"

            # Use API-specific headers
            api_headers = {
                "Authorization": f'Bearer {ConfigManager.get_config("api", "eventbrite_token")}',
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            try:
                Logger.debug(
                    "Requesting Eventbrite single event",
                    context={
                        "club_name": getattr(self.club, "name", "-"),
                        "event_id": event_id,
                        "url": retrieve_event_url,
                    },
                )
            except Exception:
                pass

            # Use base client's convenience method
            data = await self.fetch_json(
                url=retrieve_event_url,
                headers=api_headers,
                timeout=self.REQUEST_TIMEOUT,
                logger_context={"event_id": event_id},
            )

            if not data:
                self.log_warning(f"Event {event_id} not found or failed to fetch")
                return None

            resp = EventbriteSingleEventResponse.from_json_dict(data)
            try:
                Logger.debug(
                    "Parsed Eventbrite single event",
                    context={
                        "club_name": getattr(self.club, "name", "-"),
                        "event_id": event_id,
                        "name": (getattr(resp.name, "text", None) if getattr(resp, "name", None) else None),
                        "status": getattr(resp, "status", None),
                    },
                )
            except Exception:
                pass
            return resp

        except Exception as e:
            self.log_error(f"Failed to retrieve event {event_id}: {e}")
            return None
