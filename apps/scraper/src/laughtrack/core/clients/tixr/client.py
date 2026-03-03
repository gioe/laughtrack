"""
Simplified Tixr API client for fetching event details.
"""

import json
from typing import Any, Dict, List, Optional

from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.foundation.models.types import JSONDict
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.core.clients.base import BaseApiClient
from laughtrack.foundation.utilities.datetime import DateTimeUtils
from laughtrack.foundation.utilities.url import URLUtils


class TixrApiException(Exception):
    """Custom exception for Tixr API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class TixrClient(BaseApiClient):
    """
    Simplified client for interfacing with the Tixr API to fetch event details.

    Uses BaseApiClient for HTTP operations and focuses on core functionality.
    """

    def __init__(self, club: Club):
        """
        Initialize the Tixr client.

        Args:
            club: Club instance for configuration
        """
        super().__init__(club)

        # Tixr API configuration
        self.base_api_url = "https://api.tixr.com/api/events"
        self.base_url = "https://www.tixr.com"

        # Override headers for Tixr API
        self.headers.update(
            {
                "Accept": "application/json",
                "Referer": self.base_url,
            }
        )

    async def get_event_detail(self, event_id: str) -> Optional[TixrEvent]:
        """
        Get event details from Tixr API for a specific event ID.

        Args:
            event_id: The Tixr event ID

        Returns:
            TixrEvent object if successful, None otherwise
        """
        api_url = f"{self.base_api_url}/{event_id}"

        try:
            data = await self.fetch_json(url=api_url, logger_context={"event_id": event_id})

            if not data:
                self.log_warning(f"No data returned for event {event_id}")
                return None

            # Create Show object from the data
            show = self._create_show_from_data(data)
            if not show:
                self.log_warning(f"Failed to create show from data for event {event_id}")
                return None

            # Return TixrEvent wrapping the Show
            return TixrEvent.from_tixr_show(show=show, source_url=api_url, event_id=event_id)

        except Exception as e:
            self.log_error(f"Failed to fetch event {event_id}: {e}")
            return None

    async def get_event_detail_from_url(self, url: str) -> Optional[TixrEvent]:
        """
        Extract event ID from URL and fetch event details.

        Args:
            url: Tixr event page URL

        Returns:
            TixrEvent object if successful, None otherwise
        """
        event_id = URLUtils.extract_event_id_from_url(url)
        if not event_id:
            self.log_warning(f"Could not extract event ID from URL: {url}")
            return None

        return await self.get_event_detail(event_id)

    async def fetch_events(self, *args, **kwargs) -> List[JSONDict]:
        """
        Fetch events from Tixr API.

        Note: TixrClient is designed to work with specific event IDs/URLs
        rather than fetching lists of events. This method is required by
        the BaseApiClient interface.

        Returns:
            Empty list (Tixr client works with specific event requests)
        """
        self.log_info("TixrClient works with specific event IDs/URLs, not general event fetching")
        return []

    def _create_show_from_data(self, data: JSONDict) -> Optional[Show]:
        """
        Create a Show object from parsed Tixr API data.

        Args:
            data: Parsed JSON data from Tixr API

        Returns:
            Show object if successful, None otherwise
        """
        try:
            # Validate response structure
            if not isinstance(data, dict):
                self.log_warning("Invalid response format: expected dict")
                return None

            # Extract basic event information
            name = data.get("name", "")
            event_id = data.get("id", "")

            # Extract venue timezone if available
            timezone = None
            venue_data = data.get("venue", {})
            if isinstance(venue_data, dict):
                timezone = venue_data.get("timezone")

            # Parse event date
            date = None
            formatted_iso = data.get("formattedISOStartDate")
            if formatted_iso:
                date = DateTimeUtils.parse_datetime_with_timezone(formatted_iso, timezone)

            # Skip events without valid date
            if not date:
                self.log_warning(f"Event {event_id} has no valid date, skipping")
                return None

            # Build show page URL
            show_page_url = self._build_show_page_url(data, event_id)

            # Extract description
            description = data.get("description")

            # Extract lineup/comedians
            lineup = self._extract_lineup(data)

            # Extract ticket information
            tickets = self._extract_ticket_info(data, show_page_url)

            # Default values for fields not available in Tixr API
            supplied_tags = ["event"]  # Default tag as per project pattern
            room = ""  # Default empty room as per project pattern

            return Show(
                name=name,
                club_id=self.club.id,
                date=date,
                show_page_url=show_page_url,
                lineup=lineup,
                tickets=tickets,
                supplied_tags=supplied_tags,
                description=description,
                timezone=timezone,
                room=room,
            )

        except Exception as e:
            self.log_error(f"Failed to create show from Tixr data: {e}")
            return None

    def _build_show_page_url(self, data: dict, event_id: str) -> str:
        """
        Build the public show page URL from event data.

        Args:
            data: Event data from API
            event_id: Event ID

        Returns:
            Public URL for the event page
        """
        # Try to get URL from response data first
        if data.get("url"):
            return data["url"]

        # Build URL from group subdomain and event info
        group_data = data.get("group", {})
        subdomain = group_data.get("subdomain", "")

        if subdomain:
            # Use short name if available, otherwise use event name
            short_name = data.get("shortName", "")
            if not short_name:
                short_name = data.get("name", "").replace(" ", "-").lower()

            return f"https://www.tixr.com/groups/{subdomain}/events/{short_name}-{event_id}"

        # Fallback URL format
        return f"https://www.tixr.com/groups/events/{event_id}"

    def _extract_lineup(self, data: dict) -> List[Comedian]:
        """
        Extract comedian lineup from event data.

        Args:
            data: Event data from API

        Returns:
            List of Comedian objects
        """
        lineup = []

        # Check for lineups in the response
        lineups_data = data.get("lineups", [])
        if isinstance(lineups_data, list):
            for lineup_entry in lineups_data:
                if not isinstance(lineup_entry, dict):
                    continue

                acts = lineup_entry.get("acts", [])
                if isinstance(acts, list):
                    for act in acts:
                        if isinstance(act, dict):
                            # Tixr structure: act.artist.name
                            artist = act.get("artist", {})
                            if isinstance(artist, dict):
                                artist_name = artist.get("name", "").strip()
                                if artist_name:
                                    lineup.append(Comedian(name=artist_name))
                        elif isinstance(act, str) and act.strip():
                            # Fallback for direct string names
                            lineup.append(Comedian(name=act.strip()))

        # Also check for artists field (alternative structure)
        artists_data = data.get("artists", [])
        if isinstance(artists_data, list):
            for artist in artists_data:
                if isinstance(artist, dict):
                    artist_name = artist.get("name", "").strip()
                    if artist_name:
                        lineup.append(Comedian(name=artist_name))
                elif isinstance(artist, str) and artist.strip():
                    lineup.append(Comedian(name=artist.strip()))

        return lineup

    def _extract_ticket_info(self, data: dict, show_page_url: str) -> List[Ticket]:
        """
        Extract ticket information from event data.

        Args:
            data: Event data from API
            show_page_url: URL for purchasing tickets

        Returns:
            List of Ticket objects
        """
        tickets = []

        # Extract from sales data
        sales_data = data.get("sales", [])
        if isinstance(sales_data, list):
            for sale in sales_data:
                if not isinstance(sale, dict):
                    continue

                tiers = sale.get("tiers", [])
                if isinstance(tiers, list):
                    for tier in tiers:
                        if not isinstance(tier, dict):
                            continue

                        # Extract ticket information
                        price = tier.get("price")
                        sold_out = not tier.get("active", True)
                        ticket_type = tier.get("name", "General Admission")

                        # Validate price (should be numeric)
                        if price is not None:
                            try:
                                price = float(price)
                            except (ValueError, TypeError):
                                price = None

                        ticket = Ticket(
                            price=price or 0, purchase_url=show_page_url, sold_out=sold_out, type=ticket_type
                        )
                        tickets.append(ticket)

        # If no tickets found from sales, check for direct ticket info
        if not tickets:
            # Check for ticket URL or pricing in main event data
            ticket_url = data.get("ticketUrl", show_page_url)

            # Create a default ticket entry if event has ticket info
            if data.get("hasTickets", True):  # Assume tickets available unless specified
                ticket = Ticket(
                    price=0,  # Price not available
                    purchase_url=ticket_url,
                    sold_out=data.get("soldOut", False),
                    type="General Admission",
                )
                tickets.append(ticket)

        return tickets
