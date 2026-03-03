from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from laughtrack.core.clients.base import BaseApiClient
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.models.types import JSONDict
from laughtrack.foundation.utilities.datetime import DateTimeUtils
from laughtrack.foundation.utilities.url import URLUtils


class WixEventsClient(BaseApiClient):
    """Client for Wix events."""

    def __init__(self, club: Club):
        load_dotenv()
        super().__init__(club)
        # Domain without scheme for header context, base_url with scheme for requests
        self.domain = URLUtils.get_formatted_domain(self.club.scraping_url)
        self.base_url = URLUtils.get_base_domain_with_protocol(self.club.scraping_url)

        # Initialize token headers using mobile browser base and add required custom header
        self.token_headers = BaseHeaders.get_headers(base_type="mobile_browser", domain=self.domain)
        self.token_headers["client-binding"] = "e2814456-fed7-4d1b-a36c-ded753a23ca3"

    async def fetch_access_token(self) -> Optional[str]:
        """Fetch a short-lived access token required by Wix APIs."""
        self.token_url = URLUtils.build_url(self.base_url, "/_api/v1/access-tokens")
        data = await self.fetch_json(self.token_url, headers=self.token_headers)
        return self.parse_access_token_response(data) if data else None

    def parse_access_token_response(self, data: JSONDict) -> Optional[str]:
        try:
            apps = data.get("apps", {})
            auth_token = self.find_instance_by_int_id(apps, 24)
            return auth_token
        except Exception as e:
            self.log_warning(f"Error extracting token: {e}")
            return None

    def find_instance_by_int_id(self, apps: Dict[str, Dict], target_int_id: int) -> Optional[str]:
        for app_data in apps.values():
            if app_data.get("intId") == target_int_id:
                return app_data.get("instance")
        return None

    def _create_tickets(self, event: JSONDict) -> List[Ticket]:
        """
        Create Ticket objects from event registration data.

        Args:
            event: Event data from Wix API

        Returns:
            List of Ticket objects
        """
        tickets = []
        try:
            registration = event.get("registration", {})
            ticketing = registration.get("ticketing", {})

            # Get the show URL for purchase_url
            show_url = f"{self.base_url}/events/{event.get('slug', '')}"

            # Create a ticket with the lowest price
            if ticketing.get("lowestTicketPrice"):
                price_data = ticketing["lowestTicketPrice"]
                price = float(price_data.get("amount", 0))

                ticket = Ticket(
                    price=price,
                    purchase_url=show_url,
                    sold_out=ticketing.get("soldOut", False),
                    type="General Admission",  # Default type since Wix doesn't specify
                )
                tickets.append(ticket)

        except Exception as e:
            self.log_error(f"Failed to create tickets from Wix event: {e}")

        return tickets

    def create_show(self, event: JSONDict) -> Optional[Show]:
        """
        Convert a Wix event object into a Show object.

        Args:
            event: Event data from Wix API

        Returns:
            Optional[Show]: Show object if successful, None otherwise
        """
        try:
            # Extract basic show info - only including valid Show model properties
            show_info = {
                "name": event.get("title", ""),
                "description": event.get("description", ""),
                "show_page_url": f"{self.base_url}/events/{event.get('slug', '')}",
                "date": DateTimeUtils.parse_datetime_with_timezone(
                    event.get("scheduling", {}).get("config", {}).get("startDate"),
                    event.get("scheduling", {}).get("config", {}).get("timeZoneId", "America/New_York"),
                ),
                "timezone": event.get("scheduling", {}).get("config", {}).get("timeZoneId", "America/New_York"),
                "club_id": self.club.id,
                "room": event.get("location", {}).get("name", ""),
            }

            # Extract lineup from description if available
            lineup = []
            if event.get("description"):
                # Look for patterns like "Featuring X, Y, & More!" or "Featuring X, Y, and Z"
                description = event["description"]
                if "Featuring" in description:
                    # Extract names between "Featuring" and "& More!" or end of string
                    names_text = description.split("Featuring")[1].split("& More!")[0].strip()
                    # Split by commas and clean up each name
                    names = [name.strip() for name in names_text.split(",")]
                    # Remove any empty strings and create Comedian objects
                    lineup = [Comedian(name) for name in names if name]

            # Create tickets from registration data
            tickets = self._create_tickets(event)

            # Create and return the show with lineup and tickets
            return Show.create(**show_info, lineup=lineup, tickets=tickets)

        except Exception as e:
            self.log_error(f"Failed to create show from Wix event: {e}")
            return None

    async def get_shows(self) -> List[Show]:
        """
        Fetch all events from Wix API with pagination.

        Returns:
            List of Show objects from all pages
        """
        access_token = await self.fetch_access_token()
        if not access_token:
            self.log_warning("No access token received from Wix; aborting get_shows")
            return []

        base_url = URLUtils.build_url(self.base_url, "/_api/wix-one-events-server/web/paginated-events/viewer")
        all_shows = []
        offset = 0
        limit = 4

        # Use default create_show if no callback provided

        while True:
            # Build URL with current offset
            params = {
                "offset": offset,
                "filter": 1,
                "byEventId": "false",
                "members": "true",
                "paidPlans": "false",
                "locale": "en",
                "categoryId": "41b1dace-b9ba-49dd-a961-f48839c0fce0",
                "filterType": 2,
                "sortOrder": 0,
                "limit": limit,
                "draft": "false",
                "compId": "comp-lzt5zlma",
            }

            url = URLUtils.build_url(base_url, params=params)

            # Make request for current page using BaseApiClient helper
            data = await self.fetch_json(url, headers=self.build_headers(access_token))

            if not data:
                break

            try:
                events = data.get("events", [])

                # Process each event through the callback
                for event in events:
                    show = self.create_show(event)
                    if show:
                        all_shows.append(show)

                # Check if there are more events to fetch
                if not data.get("hasMore", False):
                    break

                # Increment offset for next page
                offset += limit

            except Exception as e:
                self.log_error(f"Error processing events page at offset {offset}: {e}")
                break

        return all_shows

    async def fetch_events(self, limit: int = 100) -> List[Any]:
        """Fetch events from Wix API."""
        # WixEventsClient has its own get_shows method that handles pagination
        # This method is required by the interface
        return []

    def build_headers(self, access_token: str) -> Dict[str, str]:
        """Build headers for Wix API requests."""
        headers = BaseHeaders.get_headers(base_type="json")
        headers["Authorization"] = f"Bearer {access_token}"
        return headers
