"""
LiveNation client for scraping Live Nation event pages.

This client handles Live Nation's anti-scraping protection with:
- Conservative rate limiting (1 request per 10 seconds)
- Realistic browser headers with mobile Android user agent
- Cookie management and session persistence
- JSON-LD data extraction from event pages
- Careful error handling to avoid detection

⚠️ CRITICAL: Live Nation is EXTREMELY sensitive to scraping.
Always use this client instead of direct HTTP requests.
"""

import random
import time
from typing import List, Optional

import requests

from laughtrack.foundation.models.types import JSONDict
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor
from laughtrack.core.clients.base import BaseApiClient
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.datetime import DateTimeUtils


class LiveNationClient(BaseApiClient):
    """
    Specialized client for Live Nation pages with anti-scraping protection.

    Features:
    - Conservative rate limiting (1 request per 10 seconds minimum)
    - Realistic mobile browser headers
    - Cookie management for session persistence
    - JSON-LD data extraction from event pages
    - Built-in error handling and retry logic
    """

    # API Configuration - DO NOT USE WITHOUT EXTREME CAUTION
    TICKET_API_KEY = "b462oi7fic6pehcdkzony5bxhe"
    TICKET_API_SECRET = "pquzpfrfz7zd2ylvtz3w5dtyse"

    def __init__(self, club: Club):
        super().__init__(club)

        # CRITICAL: Conservative rate limiting for Live Nation
        self.last_request_time = 0
        self.min_delay = 10.0  # 10 seconds minimum between requests
        self.max_delay = 15.0  # Random delay up to 15 seconds

        # Initialize headers for Live Nation scraping (mobile Android)
        self.headers = BaseHeaders.get_headers(
            base_type="mobile_browser",
            domain="https://concerts.livenation.com",
            origin="https://concerts.livenation.com",
            referer="https://concerts.livenation.com/",
        )
        # Add ephemeral correlation id and cookies
        self.headers.update(
            {
                "priority": "u=1, i",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-site",
                "tmps-correlation-id": self._generate_correlation_id(),
                "cookie": self._get_session_cookies(),
            }
        )

        # Separate headers for ticket API (if needed)
        self.ticket_headers = BaseHeaders.get_headers(
            base_type="json", origin="https://concerts.livenation.com", referer="https://concerts.livenation.com/"
        )

    def _generate_correlation_id(self) -> str:
        """Generate a realistic correlation ID for requests."""
        import uuid

        return str(uuid.uuid4())

    def _get_session_cookies(self) -> str:
        """
        Get realistic session cookies for Live Nation.

        Note: These are example cookies - real implementation would need
        to handle dynamic cookie generation and session management.
        """
        return (
            "eps_sid=df68d7ff9462d4321e376e585e609c39b35b3ded; "
            "_gcl_au=1.1.1660551012.1738005926; "
            "mt.pc=2.1; "
            "LANGUAGE=en-us; "
            "OptanonGroups=,C0001,C0002,C0003,C0004,; "
            "_gid=GA1.2.1385295466.1738781206"
        )

    def _enforce_rate_limit(self) -> None:
        """
        Enforce conservative rate limiting for Live Nation requests.

        ⚠️ CRITICAL: Live Nation is extremely sensitive to request frequency.
        Always call this before making any request.
        """
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        # Calculate delay with randomization
        base_delay = self.min_delay
        random_delay = random.uniform(0, self.max_delay - self.min_delay)
        required_delay = base_delay + random_delay

        if time_since_last < required_delay:
            sleep_time = required_delay - time_since_last
            self.log_info(f"Rate limiting: sleeping {sleep_time:.1f}s before Live Nation request")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    async def fetch_events(self, venue_id: str) -> List[JSONDict]:
        """
        Fetch events from Live Nation venue page.

        ⚠️ WARNING: This method is not implemented yet to prevent
        accidental API calls during development.

        Args:
            venue_id: Live Nation venue identifier

        Returns:
            List of event dictionaries
        """
        self.log_warning("fetch_events called but not implemented - preventing accidental API calls")
        return []

    def scrape_event_page(self, event_url: str) -> Optional[Show]:
        """
        Scrape a single Live Nation event page for show details.

        ⚠️ WARNING: This method makes real HTTP requests. Use with extreme caution.

        Args:
            event_url: URL of the Live Nation event page

        Returns:
            Show object if successful, None otherwise
        """
        try:
            # Enforce rate limiting before any request
            self._enforce_rate_limit()

            self.log_info(f"Scraping Live Nation event page: {event_url}")

            # Make HTTP request with protection
            response = requests.get(event_url, headers=self.headers, timeout=30)

            if response.status_code != 200:
                self.log_warning(f"HTTP {response.status_code} for {event_url}")
                return None

            return self._create_show_from_response(response)

        except Exception as e:
            self.log_error(f"Error scraping Live Nation page {event_url}: {e}")
            return None

    def _create_show_from_response(self, response: requests.Response) -> Optional[Show]:
        """
        Create a Show object from Live Nation page response.

        Args:
            response: HTTP response from Live Nation event page

        Returns:
            Show object if successful, None otherwise
        """
        try:
            json_ld_data_list = EventExtractor.extract_events(response.text)

            if not json_ld_data_list:
                self.log_warning(f"No JSON-LD data found on page: {response.url}")
                return None

            # Use the first event found and convert via Event API
            primary_event = json_ld_data_list[0]
            show_obj_any = primary_event.to_show(club=self.club, enhanced=True)
            if not show_obj_any:
                return None
            from typing import cast
            show_obj = cast(Show, show_obj_any)
            # Construct a new Show ensuring timezone and tag
            return Show.create(
                name=show_obj.name,
                club_id=self.club.id,
                date=show_obj.date,
                show_page_url=show_obj.show_page_url,
                lineup=show_obj.lineup,
                tickets=show_obj.tickets,
                description=show_obj.description,
                room=show_obj.room if hasattr(show_obj, "room") else "",
                supplied_tags=(getattr(show_obj, "supplied_tags", []) or []) + ["livenation"],
                timezone=self.club.timezone,
            )

        except KeyError as key:
            self.log_warning(f"Missing required field {key} in Live Nation data")
        except Exception as e:
            self.log_error(f"Error processing Live Nation data: {e}")

        return None

    def _extract_basic_show_info(self, json_ld_data: JSONDict) -> Optional[JSONDict]:
        """
        Extract basic show information from JSON-LD data.

        Args:
            json_ld_data: JSON-LD structured data from the page

        Returns:
            Dictionary with basic show information or None if extraction fails
        """
        try:
            # Parse date from ISO8601 format
            start_date = json_ld_data.get("startDate")
            if not start_date:
                self.log_warning("No startDate found in JSON-LD data")
                return None

            formatted_date = DateTimeUtils.parse_datetime_with_timezone(start_date, self.club.timezone)

            # Extract lineup from performers
            lineup = []
            performers = json_ld_data.get("performer", [])
            if isinstance(performers, dict):
                performers = [performers]

            for performer in performers:
                if isinstance(performer, dict) and performer.get("name"):
                    lineup.append(Comedian(name=performer["name"]))

            return {
                "name": json_ld_data.get("name", ""),
                "date": formatted_date,
                "description": json_ld_data.get("description", ""),
                "show_page_url": json_ld_data.get("url", ""),
                "lineup": lineup,
            }

        except Exception as e:
            self.log_error(f"Error extracting basic show info: {e}")
            return None

    def _extract_ticket_data(self, json_ld_data: JSONDict) -> List[Ticket]:
        """
        Extract ticket information from JSON-LD offers data.

        Args:
            json_ld_data: JSON-LD structured data from the page

        Returns:
            List of Ticket objects
        """
        tickets = []

        try:
            offers = json_ld_data.get("offers", [])
            if isinstance(offers, dict):
                offers = [offers]

            for offer in offers:
                try:
                    # Extract price (handle both string and number formats)
                    price = offer.get("price", 0)
                    if isinstance(price, str):
                        # Remove currency symbols and convert to float
                        price = float(price.replace("$", "").replace(",", ""))

                    # Check availability
                    availability = offer.get("availability", "")
                    sold_out = "SoldOut" in availability or "OutOfStock" in availability

                    tickets.append(
                        Ticket(
                            price=float(price),
                            purchase_url=offer.get("url", ""),
                            sold_out=sold_out,
                            type=offer.get("category", "General Admission"),
                        )
                    )

                except (ValueError, TypeError) as e:
                    Logger.warn(f"Error parsing ticket offer: {e}", {"club": self.club.name})
                    continue

        except Exception as e:
            Logger.warn(f"Error extracting ticket data: {e}", {"club": self.club.name})

        return tickets

    def make_ticket_api_url(self, ticketmaster_id: str) -> str:
        """
        Generate Live Nation ticket API URL.

        ⚠️ WARNING: This API endpoint should only be used with extreme caution
        and proper rate limiting. Live Nation may block excessive usage.

        Args:
            ticketmaster_id: TicketMaster event ID

        Returns:
            API URL for ticket information
        """
        return (
            f"https://services.livenation.com/api/ismds/event/{ticketmaster_id}/facets"
            f"?show=totalpricerange"
            f"&by=offers"
            f"&q=available"
            f"&apikey={self.TICKET_API_KEY}"
            f"&apisecret={self.TICKET_API_SECRET}"
            f"&resaleChannelId=internal.ecommerce.consumer.desktop.web.browser.livenation.us"
        )

    def create_show(self, event_data: JSONDict) -> Optional[Show]:
        """
        Convert event data from Live Nation API to a Show object.

        Args:
            event_data: Raw event data from Live Nation API

        Returns:
            Show object if successful, None otherwise
        """
        try:
            # Extract basic show information
            show_data = self._extract_basic_show_info_from_api(event_data)
            if not show_data:
                return None

            # Extract ticket information if available
            tickets = self._extract_ticket_data_from_api(event_data)

            # Create show with all data
            show_data.update(
                {
                    "tickets": tickets,
                    "club_id": self.club.id,
                    "timezone": self.club.timezone,
                    "room": "",  # Live Nation doesn't typically specify rooms
                    "supplied_tags": ["livenation"],  # Tag as Live Nation event
                }
            )

            return Show.create(**show_data)

        except Exception as e:
            Logger.error(f"Error processing Live Nation data: {e}", {"club": self.club.name})
            return None

    def _extract_basic_show_info_from_api(self, event_data: JSONDict) -> Optional[JSONDict]:
        """
        Extract basic show information from Live Nation API data.

        Args:
            event_data: Raw event data from Live Nation API

        Returns:
            Dictionary with basic show information or None if extraction fails
        """
        try:
            # Parse date from API format
            start_date = event_data.get("startDate") or event_data.get("date")
            if not start_date:
                Logger.warn("No startDate/date found in API data", {"club": self.club.name})
                return None

            formatted_date = DateTimeUtils.parse_datetime_with_timezone(start_date, self.club.timezone)

            # Extract lineup from API data
            lineup = []
            performers = event_data.get("performers", []) or event_data.get("artists", [])
            if isinstance(performers, dict):
                performers = [performers]

            for performer in performers:
                if isinstance(performer, dict) and performer.get("name"):
                    lineup.append(Comedian(name=performer["name"]))
                elif isinstance(performer, str):
                    lineup.append(Comedian(name=performer))

            return {
                "name": event_data.get("name", ""),
                "date": formatted_date,
                "description": event_data.get("description", ""),
                "show_page_url": event_data.get("url", ""),
                "lineup": lineup,
            }

        except Exception as e:
            Logger.error(f"Error processing Live Nation data: {e}", {"club": self.club.name})
            return None

    def _extract_ticket_data_from_api(self, event_data: JSONDict) -> List[Ticket]:
        """
        Extract ticket information from Live Nation API data.

        Args:
            event_data: Raw event data from Live Nation API

        Returns:
            List of Ticket objects
        """
        tickets = []

        try:
            # Check for ticket information in API response
            offers = event_data.get("offers", []) or event_data.get("ticketing", {}).get("offers", [])
            if isinstance(offers, dict):
                offers = [offers]

            for offer in offers:
                try:
                    # Extract price (handle both string and number formats)
                    price = offer.get("price", 0) or offer.get("priceRange", {}).get("minPrice", 0)
                    if isinstance(price, str):
                        # Remove currency symbols and convert to float
                        price = float(price.replace("$", "").replace(",", ""))

                    # Check availability
                    availability = offer.get("availability", "") or offer.get("status", "")
                    sold_out = "SoldOut" in availability or "Unavailable" in availability

                    tickets.append(
                        Ticket(
                            price=float(price),
                            purchase_url=offer.get("url", ""),
                            sold_out=sold_out,
                            type=offer.get("category", "General Admission"),
                        )
                    )

                except (ValueError, TypeError) as e:
                    Logger.warn(f"Error parsing API ticket offer: {e}", {"club": self.club.name})
                    continue

        except Exception as e:
            Logger.error(f"Error processing Live Nation data: {e}", {"club": self.club.name})

        return tickets


def create_live_nation_client(club: Club) -> LiveNationClient:
    """
    Factory function to create a LiveNation client with proper configuration.

    Args:
        club: Club instance for Live Nation venue

    Returns:
        Configured LiveNationClient instance
    """
    return LiveNationClient(club)
