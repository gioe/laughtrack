from typing import Any, Callable, Dict, List, Optional

from curl_cffi.requests import Response

from laughtrack.foundation.models.request_data import RequestData
from laughtrack.foundation.models.types import JSONDict
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool
from laughtrack.core.clients.base import BaseApiClient
from laughtrack.foundation.utilities.datetime import DateTimeUtils
from laughtrack.foundation.utilities.url import URLUtils


class SeatEngineClient(BaseApiClient):
    """Client for interacting with SeatEngine's API."""

    def __init__(self, club: Club, proxy_pool: Optional[ProxyPool] = None):
        """Initialize the client with club data."""
        super().__init__(club, proxy_pool=proxy_pool)
        domain = URLUtils.get_formatted_domain(club.scraping_url)
        self.headers = BaseHeaders.get_headers(
            base_type="mobile_browser",
            auth_type="seat_engine",
            auth_token="3c7de746-6bc2-4efb-8e91-16da6155edce",
            domain=domain,
        )
        # Use seatengine_id directly from club if available
        self.venue_id = club.seatengine_id

    async def fetch_events(self, venue_id: str) -> List[JSONDict]:
        """Fetch events from SeatEngine API.

        Args:
            venue_id: The venue identifier for SeatEngine

        Returns:
            List of event dictionaries from SeatEngine API
        """
        try:
            events_url = f"https://services.seatengine.com/api/v1/venues/{venue_id}/shows"

            data = await self.fetch_json(events_url, headers=self.headers)
            if not data:
                self.log_error("No response received from SeatEngine API")
                return []

            shows = data.get("data", data.get("shows", []))
            self.log_info(f"Extracted {len(shows)} shows from response")
            return shows

        except Exception as e:
            self.log_error(f"Failed to fetch events from SeatEngine: {e}")
            return []

    async def get_ticket_data(self, show_id: str, callback: Optional[Callable[[Response], Any]] = None) -> Optional[JSONDict]:
        """
        Get ticket data from SeatEngine for a given show URL.

        Args:
            url: The show URL to get ticket data for

        Returns:
            Optional[JSONDict]: Dictionary containing ticket data with URL included, or None if failed
        """
        try:
            ticket_url = f"https://services.seatengine.com/api/v1/venues/{self.venue_id}/shows/{show_id}"
            # For now, just return parsed JSON
            return await self.fetch_json(ticket_url, headers=self.headers)
        except Exception as e:
            return None

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

        return {
            "name": event_data.get("name"),
            "date": parsed_date,
            "show_page_url": f"https://services.seatengine.com/api/v1/venues/{self.venue_id}/shows/{show_dict.get('id')}",
            "description": event_data.get("description"),
            "tickets": self._extract_ticket_data(show_dict),
        }

    def _extract_ticket_data(self, show_dict: JSONDict) -> List[Ticket]:
        """Extract ticket information from the SeatEngine show data."""
        # For SeatEngine, we create a basic ticket with show URL for now
        # In a real implementation, you might need to make an additional API call
        # to get detailed pricing information

        event_data = show_dict.get("event", {})
        tickets = []

        # Create a basic ticket entry if the show is available
        if not show_dict.get("sold_out", False):
            ticket = Ticket(
                price=0.0,  # Would need additional API call for actual pricing
                purchase_url=f"https://services.seatengine.com/api/v1/venues/{self.venue_id}/shows/{show_dict.get('id')}",
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

        Args:
            venue_id: The venue identifier for SeatEngine

        Returns:
            Dictionary containing venue details from SeatEngine API, or None if failed
        """
        try:
            venue_url = f"https://services.seatengine.com/api/v1/venues/{venue_id}"
            self.log_info(f"Fetching SeatEngine venue details from: {venue_url}")

            request_data = RequestData.get(url=venue_url, headers=self.headers)
            response = None

            if response:
                try:
                    response_json = response.json()

                    if response_json and "data" in response_json:
                        venue_data = response_json["data"]
                        return venue_data
                    else:
                        return None

                except Exception as json_error:
                    self.log_error(f"Failed to parse SeatEngine venue response as JSON: {json_error}")
                    return None
            else:
                self.log_error("No response received from SeatEngine venue API")
                return None

        except Exception as e:
            self.log_error(f"Failed to fetch venue details from SeatEngine: {e}")
            return None
