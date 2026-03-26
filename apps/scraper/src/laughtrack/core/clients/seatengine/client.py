from typing import Any, Callable, Dict, List, Optional

from curl_cffi.requests import Response

from laughtrack.foundation.models.types import JSONDict
from laughtrack.foundation.exceptions import CircuitBreakerOpenError, NetworkError
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool
from laughtrack.core.clients.base import BaseApiClient
from laughtrack.core.clients.seatengine.circuit_breaker import SeatEngineCircuitBreaker
from laughtrack.foundation.utilities.datetime import DateTimeUtils
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.infrastructure.config.config_manager import ConfigManager


class SeatEngineClient(BaseApiClient):
    """Client for interacting with SeatEngine's API."""

    def __init__(self, club: Club, proxy_pool: Optional[ProxyPool] = None):
        """Initialize the client with club data."""
        super().__init__(club, proxy_pool=proxy_pool)
        domain = URLUtils.get_formatted_domain(URLUtils.normalize_url(club.scraping_url))
        auth_token = ConfigManager.get_config("api", "seatengine_auth_token")
        self.headers = BaseHeaders.get_headers(
            base_type="mobile_browser",
            auth_type="seat_engine",
            auth_token=auth_token,
            domain=domain,
        )
        # Use seatengine_id directly from club if available
        self.venue_id = club.seatengine_id
        # Populated by fetch_events from GET /api/v1/venues/{id} — used for public show URLs
        self.venue_website: Optional[str] = None

    async def fetch_events(self, venue_id: str) -> List[JSONDict]:
        """Fetch events from SeatEngine API.

        Args:
            venue_id: The venue identifier for SeatEngine

        Returns:
            List of event dictionaries from SeatEngine API

        Raises:
            CircuitBreakerOpenError: If the shared circuit breaker is open (API is down).
            NetworkError: If the API returns no data (non-200 response).
        """
        cb = SeatEngineCircuitBreaker()
        cb.check_open()

        try:
            events_url = f"https://services.seatengine.com/api/v1/venues/{venue_id}/shows"
            data = await self.fetch_json(events_url, headers=self.headers)

            if data is None:
                cb.record_failure()
                # status_code=None because fetch_json() absorbs the status code.
                # ErrorHandler._should_retry() treats None-status NetworkErrors as
                # retryable, so each retry attempt records another failure — the
                # circuit breaker will open after (threshold / max_retries) venues
                # rather than exactly `threshold` venues. This is intentional: rapid
                # consecutive failures (retries) are a strong outage signal.
                raise NetworkError(
                    f"SeatEngine API returned no data for venue {venue_id}",
                    status_code=None,
                )

            cb.record_success()
            shows = data.get("data", data.get("shows", []))
            self.log_info(f"Extracted {len(shows)} shows from response")

            # Fetch venue website once per scrape run for public show URL construction.
            # Isolated try/except prevents any failure here from contaminating the
            # circuit breaker (which should only track shows-endpoint health).
            if self.venue_website is None:
                try:
                    venue = await self.fetch_venue_details(venue_id)
                    # Use "" as a sentinel for "fetched but no website" so we don't
                    # re-fetch on retries when the API returns no website field.
                    self.venue_website = (venue.get("website") or "").rstrip("/") if venue else ""
                except Exception as e:
                    self.log_warning(f"Failed to fetch venue website for {venue_id}: {e}")
                    self.venue_website = ""

            return shows

        except (CircuitBreakerOpenError, NetworkError):
            raise
        except Exception as e:
            cb.record_failure()
            raise NetworkError(f"Failed to fetch events from SeatEngine: {e}") from e

    async def get_ticket_data(self, show_id: str, callback: Optional[Callable[[Response], Any]] = None) -> Optional[JSONDict]:
        """
        Get ticket data from SeatEngine for a given show URL.

        Args:
            show_id: The show identifier to fetch ticket data for

        Returns:
            Optional[JSONDict]: Dictionary containing ticket data, or None if failed

        Raises:
            CircuitBreakerOpenError: If the shared circuit breaker is open (API is down).
            NetworkError: If the API returns no data (non-200 response).
        """
        cb = SeatEngineCircuitBreaker()
        cb.check_open()

        try:
            ticket_url = f"https://services.seatengine.com/api/v1/venues/{self.venue_id}/shows/{show_id}"
            data = await self.fetch_json(ticket_url, headers=self.headers)
            if data is None:
                # Per-show failures are intentionally NOT recorded against the circuit
                # breaker — individual show 404s are too noisy to be reliable outage
                # signals. Only fetch_events() (venue-level) drives the failure counter.
                raise NetworkError(
                    f"SeatEngine API returned no data for show {show_id}",
                    status_code=None,
                )
            # A successful ticket fetch signals the API is reachable — reset the counter
            # in case a prior fetch_events() failure left the count partially elevated.
            cb.record_success()
            return data
        except (CircuitBreakerOpenError, NetworkError):
            raise
        except Exception as e:
            raise NetworkError(f"Failed to fetch ticket data from SeatEngine: {e}") from e

    def create_show(self, show_dict: JSONDict) -> Optional[Show]:
        """Create a Show object from the SeatEngine response data."""
        show_info = self._extract_basic_show_info(show_dict)

        # Extract performers from the event's talents array
        event_data = show_dict.get("event", {})
        talents = event_data.get("talents", [])
        lineup = [Comedian(talent.get("name", "")) for talent in talents if talent.get("name")]

        room = self._check_room(event_data)

        return Show.create(**show_info, lineup=lineup, timezone=self.club.timezone, club_id=self.club.id, room=room)

    def _extract_basic_show_info(self, show_dict: JSONDict) -> JSONDict:
        # SeatEngine has a nested structure where event details are in the 'event' object
        event_data = show_dict.get("event", {})

        # Parse the ISO date string into a datetime object first
        date_str = show_dict.get("start_date_time")
        parsed_date = None
        if date_str:
            try:
                parsed_date = DateTimeUtils.parse_datetime_with_timezone(date_str, self.club.timezone)
                parsed_date = DateTimeUtils.format_utc_iso_date(parsed_date)
            except Exception as e:
                self.log_error(f"Failed to parse date '{date_str}': {e}")
                parsed_date = None

        show_id = show_dict.get("id")
        if self.venue_website:
            show_page_url = f"{self.venue_website}/shows/{show_id}"
        else:
            show_page_url = f"https://services.seatengine.com/api/v1/venues/{self.venue_id}/shows/{show_id}"

        return {
            "name": event_data.get("name"),
            "date": parsed_date,
            "show_page_url": show_page_url,
            "description": event_data.get("description"),
            "tickets": self._extract_ticket_data(show_dict),
        }

    def _extract_ticket_data(self, show_dict: JSONDict) -> List[Ticket]:
        """Extract ticket information from the SeatEngine show data."""
        show_id = show_dict.get("id")
        if self.venue_website:
            purchase_url = f"{self.venue_website}/shows/{show_id}"
        else:
            purchase_url = f"https://services.seatengine.com/api/v1/venues/{self.venue_id}/shows/{show_id}"

        tickets = []

        if not show_dict.get("sold_out", False):
            # Extract price from inventories if present (integer cents → float dollars)
            inventories = show_dict.get("inventories", [])
            price = 0.0
            if inventories:
                price = (inventories[0].get("price") or 0) / 100

            ticket = Ticket(
                price=price,
                purchase_url=purchase_url,
                sold_out=show_dict.get("sold_out", False),
                type="General Admission",
            )
            tickets.append(ticket)

        return tickets

    def _check_room(self, event_data: JSONDict) -> Optional[str]:
        """Check if the show is in a specific room based on event labels."""
        labels = [label.get("name") for label in event_data.get("labels", [])]
        room = None
        if "Main Room" in labels:
            room = "Main Room"
        elif "The Giggle Room" in labels:
            room = "The Giggle Room"
        # Check if "Room 861" is in the show name (common pattern for this venue)
        elif "Room 861" in event_data.get("name", ""):
            room = "Room 861"
        return room

    async def fetch_venue_details(self, venue_id: str) -> Optional[JSONDict]:
        """Fetch venue details from SeatEngine API.

        Called by fetch_events to cache venue_website for public show URL construction,
        and by the dev tool at apps/scraper/web/seatengine_api_tool/app.py.

        Args:
            venue_id: The venue identifier for SeatEngine

        Returns:
            Dictionary containing venue details from SeatEngine API, or None if failed
        """
        try:
            venue_url = f"https://services.seatengine.com/api/v1/venues/{venue_id}"
            self.log_info(f"Fetching SeatEngine venue details from: {venue_url}")

            data = await self.fetch_json(venue_url, headers=self.headers)
            if not data:
                self.log_error("No response received from SeatEngine venue API")
                return None

            return data.get("data", data)

        except Exception as e:
            self.log_error(f"Failed to fetch venue details from SeatEngine: {e}")
            return None
