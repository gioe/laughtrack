"""
Ticketmaster Developer API client.

This client uses the official Ticketmaster Discovery API for legitimate API access:
- Official API endpoints with proper authentication
- No browser simulation or anti-scraping measures needed
- Standard rate limiting (5000 requests per day, 5 per second)
- Clean JSON API responses
- Comprehensive event and venue data

Documentation: https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/
"""

import time
from datetime import datetime, timedelta
from typing import List, Optional

from laughtrack.core.clients.base import BaseApiClient
from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.foundation.models.types import JSONDict

from laughtrack.infrastructure.config.config_manager import ConfigManager
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.utilities.datetime import DateTimeUtils
from laughtrack.foundation.utilities.url import URLUtils


class TicketmasterClient(BaseApiClient):
    """
    Official Ticketmaster Discovery API client.

    Features:
    - Official API access with authentication
    - Standard rate limiting (5 requests per second)
    - Event discovery by venue, artist, or keyword
    - Venue information and event details
    - Clean JSON responses with structured data
    - No anti-scraping protection needed
    """

    # Ticketmaster Discovery API Configuration
    BASE_URL = "https://app.ticketmaster.com/discovery/v2"
    DEFAULT_MARKET = "US"  # Default to US market

    def __init__(self, club: Club, api_key: Optional[str] = None, proxy_pool: Optional[ProxyPool] = None):
        super().__init__(club, proxy_pool=proxy_pool)

        # Get API key from environment or parameter
        self.api_key = api_key or ConfigManager.get_config("api", "ticketmaster_api_key")
        if not self.api_key:
            raise ValueError(
                "Ticketmaster API key is required. Set TICKETMASTER_API_KEY environment variable "
                "or pass api_key parameter. ConfigManager will load it automatically. "
                "Get your API key from: https://developer.ticketmaster.com/"
            )

        # Standard rate limiting for API (5 requests per second)
        self.last_request_time = 0
        self.min_delay = 0.2  # 200ms between requests (5 per second)

    # Headers are initialized via BaseApiClient; override adds JSON/UA defaults

    # Use BaseApiClient session-less helpers; no custom session lifecycle needed

    def _enforce_rate_limit(self) -> None:
        """
        Enforce API rate limiting (5 requests per second).

        Ticketmaster API allows 5 requests per second and 5000 per day.
        This is much more generous than scraping rate limits.
        """
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    async def fetch_events(self, venue_id: str, **kwargs) -> List[JSONDict]:
        """
        Fetch events from Ticketmaster API for a specific venue.

        Args:
            venue_id: Ticketmaster venue ID (e.g., "KovZpZAEAaEA")
            **kwargs: Additional API parameters

        Returns:
            List of event dictionaries from API response
        """
        try:
            # Build API parameters
            params = {
                "apikey": self.api_key,
                "venueId": venue_id,
                "classificationName": "comedy",  # Focus on comedy events
                "size": 200,  # Maximum events per request
                "sort": "date,asc",  # Sort by date
                **kwargs,
            }

            # Add date range (next 6 months by default)
            if "startDateTime" not in params:
                params["startDateTime"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            if "endDateTime" not in params:
                end_date = datetime.now() + timedelta(days=180)
                params["endDateTime"] = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

            # Enforce rate limiting
            self._enforce_rate_limit()

            # Make API request
            url = f"{self.BASE_URL}/events.json"

            self.log_info(f"Fetching events from Ticketmaster API for venue {venue_id}")

            # Build full URL with query params and use BaseApiClient.fetch_json
            full_url = URLUtils.build_url(url, params=params)
            data = await self.fetch_json(full_url, headers=self.headers)

            if not data:
                self.log_warning("Ticketmaster API returned no data for events request")
                return []

            events = data.get("_embedded", {}).get("events", [])
            self.log_info(f"Successfully fetched {len(events)} events from Ticketmaster API")
            return events

        except Exception as e:
            self.log_error(f"Error fetching events from Ticketmaster API: {e}")
            return []

    async def search_venues(self, keyword: str, **kwargs) -> List[JSONDict]:
        """
        Search for venues by keyword using Ticketmaster API.

        Args:
            keyword: Search keyword (venue name, city, etc.)
            **kwargs: Additional API parameters

        Returns:
            List of venue dictionaries from API response
        """
        try:
            # Build API parameters
            params = {"apikey": self.api_key, "keyword": keyword, "size": 50, **kwargs}  # Maximum venues per request

            # Enforce rate limiting
            self._enforce_rate_limit()

            # Make API request
            url = f"{self.BASE_URL}/venues.json"

            self.log_info(f"Searching venues with keyword: {keyword}")

            full_url = URLUtils.build_url(url, params=params)
            data = await self.fetch_json(full_url, headers=self.headers)
            if not data:
                self.log_warning("Venue search returned no data")
                return []

            venues = data.get("_embedded", {}).get("venues", [])
            self.log_info(f"Found {len(venues)} venues for keyword: {keyword}")
            return venues

        except Exception as e:
            self.log_error(f"Error searching venues: {e}")
            return []

    def create_show(self, event_data: JSONDict) -> Optional[Show]:
        """
        Convert Ticketmaster API event data to a Show object.

        Args:
            event_data: Raw event data from Ticketmaster API

        Returns:
            Show object if successful, None otherwise
        """
        try:
            # Extract basic show information
            show_data = self._extract_basic_show_info_from_api(event_data)
            if not show_data:
                return None

            # Extract ticket information
            tickets = self._extract_ticket_data_from_api(event_data)

            # Create show with all data
            show_data.update(
                {
                    "tickets": tickets,
                    "club_id": self.club.id,
                    "timezone": self.club.timezone,
                    "room": self._extract_room_info(event_data),
                    "supplied_tags": ["ticketmaster", "comedy"],
                }
            )

            return Show.create(**show_data)

        except Exception as e:
            self.log_error(f"Error creating show from Ticketmaster API data: {e}")
            return None

    def _extract_basic_show_info_from_api(self, event_data: JSONDict) -> Optional[JSONDict]:
        """
        Extract basic show information from Ticketmaster API data.

        Args:
            event_data: Raw event data from Ticketmaster API

        Returns:
            Dictionary with basic show information or None if extraction fails
        """
        try:
            # Extract date and time
            dates = event_data.get("dates", {})
            start = dates.get("start", {})

            # Combine date and time
            date_str = start.get("localDate")  # YYYY-MM-DD
            time_str = start.get("localTime", "19:00:00")  # Default to 7 PM if no time

            if not date_str:
                self.log_warning("No date found in Ticketmaster event data")
                return None

            # Parse datetime
            datetime_str = f"{date_str}T{time_str}"
            formatted_date = DateTimeUtils.parse_datetime_with_timezone(datetime_str, self.club.timezone)

            # Extract lineup from attractions
            lineup = []
            attractions = event_data.get("_embedded", {}).get("attractions", [])

            for attraction in attractions:
                if attraction.get("name"):
                    lineup.append(Comedian(name=attraction["name"]))

            # Extract venue information for show page URL
            venues = event_data.get("_embedded", {}).get("venues", [])
            venue_name = venues[0].get("name", "") if venues else ""

            return {
                "name": event_data.get("name", ""),
                "date": formatted_date,
                "description": self._extract_description(event_data),
                "show_page_url": event_data.get("url", ""),
                "lineup": lineup,
            }

        except Exception as e:
            self.log_error(f"Error extracting basic show info from Ticketmaster API data: {e}")
            return None

    def _extract_ticket_data_from_api(self, event_data: JSONDict) -> List[Ticket]:
        """
        Extract ticket information from Ticketmaster API data.

        Args:
            event_data: Raw event data from Ticketmaster API

        Returns:
            List of Ticket objects
        """
        tickets = []

        try:
            # Check sales info
            sales = event_data.get("sales", {})
            public_sales = sales.get("public", {})

            # Extract price ranges
            price_ranges = event_data.get("priceRanges", [])

            if price_ranges:
                for price_range in price_ranges:
                    try:
                        min_price = price_range.get("min", 0)
                        max_price = price_range.get("max", min_price)
                        ticket_type = price_range.get("type", "General Admission")

                        # Check if sold out
                        sold_out = (
                            public_sales.get("startDateTime") is None
                            or event_data.get("dates", {}).get("status", {}).get("code") == "offsale"
                        )

                        # Create ticket for min price
                        tickets.append(
                            Ticket(
                                price=float(min_price),
                                purchase_url=event_data.get("url", ""),
                                sold_out=sold_out,
                                type=f"{ticket_type} (from ${min_price})",
                            )
                        )

                        # If there's a significant price range, add max price ticket
                        if max_price > min_price + 5:  # More than $5 difference
                            tickets.append(
                                Ticket(
                                    price=float(max_price),
                                    purchase_url=event_data.get("url", ""),
                                    sold_out=sold_out,
                                    type=f"{ticket_type} (up to ${max_price})",
                                )
                            )

                    except (ValueError, TypeError) as e:
                        self.log_warning(f"Error parsing Ticketmaster price range: {e}")
                        continue
            else:
                # No price info available, create a generic ticket
                sold_out = public_sales.get("startDateTime") is None
                tickets.append(
                    Ticket(
                        price=0.0, purchase_url=event_data.get("url", ""), sold_out=sold_out, type="General Admission"
                    )
                )

        except Exception as e:
            self.log_error(f"Error extracting ticket data from Ticketmaster API data: {e}")

        return tickets

    def _extract_description(self, event_data: JSONDict) -> str:
        """Extract event description from API data."""
        # Try different description fields
        info = event_data.get("info", "")
        pleaseNote = event_data.get("pleaseNote", "")

        # Combine available information
        description_parts = []
        if info:
            description_parts.append(info)
        if pleaseNote:
            description_parts.append(f"Please note: {pleaseNote}")

        return " | ".join(description_parts) if description_parts else ""

    def _extract_room_info(self, event_data: JSONDict) -> str:
        """Extract room/venue information from API data."""
        venues = event_data.get("_embedded", {}).get("venues", [])
        if venues:
            venue = venues[0]
            # Look for specific room/hall information
            return venue.get("name", "")
        return ""

    def _initialize_headers(self) -> dict:
        """Override default headers with JSON-focused defaults for Ticketmaster."""
        headers = BaseHeaders.get_headers(base_type="json")
        headers.update({
            "Accept": "application/json",
            "User-Agent": "LaughtrackScraper/1.0 (Comedy Show Discovery)",
        })
        return headers


async def create_ticketmaster_client(club: Club, api_key: Optional[str] = None) -> TicketmasterClient:
    """
    Factory function to create a Ticketmaster client with proper configuration.

    Args:
        club: Club instance for Ticketmaster integration
        api_key: Optional API key (uses environment variable if not provided)

    Returns:
        Configured TicketmasterClient instance
    """
    # BaseApiClient manages sessions per request; no session warm-up needed
    client = TicketmasterClient(club, api_key)
    return client
